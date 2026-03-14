import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.knowledge.loader import build_grounding_context
from app.models.schemas import FollowUpRequest, NarrativeSegment
from app.rate_limiter import limiter
from app.services.adk_orchestrator import run_adk_followup, run_adk_narrative
from app.services.gemini_service import generate_interleaved, validate_followup_question
from app.services.narrative_planner import generate_narrative_only, get_fast_arc, plan_arc_only
from app.services.trust_classifier import apply_trust_tags
from app.services.tts_service import generate_narration
from app.store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["narrative"])


@router.get("/narrative/{session_id}/stream")
@limiter.limit("10/minute")
async def stream_narrative(
    request: Request,
    session_id: UUID,
    audio: bool = Query(default=False, description="Generate TTS audio for text segments"),
    fast: bool = Query(default=True, description="Skip arc-planning Gemini call; use template for faster load"),
    use_adk: bool = Query(default=True, description="Route through the ADK agent orchestrator"),
):
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_generating:
        raise HTTPException(status_code=409, detail="Narrative already generating")

    # --- ADK-orchestrated path ---
    if use_adk:
        async def adk_event_generator():
            session.is_generating = True
            session_store.update(session)
            try:
                logger.info("[stream] ADK narrative stream started for session %s (audio=%s)", str(session_id), audio)
                async for sse_event in run_adk_narrative(session, audio=audio):
                    yield sse_event
            except Exception as e:
                logger.error(f"ADK Narrative generation error: {e}", exc_info=True)
                error_msg = "An unexpected error occurred during narrative generation. Please try again."
                if isinstance(e, ValueError):
                    error_msg = str(e)
                yield {"event": "error", "data": json.dumps({"error": error_msg})}
            finally:
                session.is_generating = False
                try:
                    session_store.update(session)
                except Exception as store_err:
                    logger.error(f"Failed to update session store in stream finally: {store_err}", exc_info=True)

        return EventSourceResponse(adk_event_generator())

    # --- Direct pipeline fallback (use_adk=false) ---
    arc_planning_timeout = 60   # seconds (Gemini text call)
    narrative_timeout = 120     # seconds (Gemini image + text call)

    async def event_generator():
        session.is_generating = True
        session_store.update(session)
        queue = asyncio.Queue()

        async def _emit(event_name: str, data: str):
            await queue.put({"event": event_name, "data": data})

        async def _orchestrator():
            try:
                logger.info("[stream] Direct pipeline stream started for session %s (fast=%s, audio=%s)", str(session_id), fast, audio)
                await _emit("status", json.dumps({"status": "generating"}))

                if fast:
                    await _emit("status", json.dumps({"status": "generating_narrative"}))
                    logger.info("[stream] Step: generating_narrative (fast mode, no arc call)")
                    arc, grounding_context = get_fast_arc(session)
                    await _emit("arc", json.dumps(arc))
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=narrative_timeout,
                    )
                else:
                    await _emit("status", json.dumps({"status": "planning_arc"}))
                    logger.info("[stream] Step: planning_arc (timeout %ss)", arc_planning_timeout)
                    arc_outline, grounding_context = await asyncio.wait_for(
                        plan_arc_only(session),
                        timeout=arc_planning_timeout,
                    )
                    await _emit("arc", json.dumps(arc_outline))

                    await _emit("status", json.dumps({"status": "generating_narrative"}))
                    logger.info("[stream] Step: generating_narrative (timeout %ss)", narrative_timeout)
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=narrative_timeout,
                    )
                logger.info("[stream] Generated %s segments, streaming to client", len(segments))

                # Stream segments immediately to queue, kick off TTS tasks in background
                tts_tasks = []
                for i, seg in enumerate(segments):
                    session.segments.append(seg)
                    await _emit(seg.type, seg.model_dump_json())

                    if audio and seg.type == "text" and seg.content and not seg.media_data:
                        async def _do_tts(s=seg):
                            try:
                                result = await generate_narration(s.content)
                                if result:
                                    audio_data, media_type = result
                                    audio_seg = NarrativeSegment(
                                        type="audio",
                                        content=s.content[:100] if s.content else "",
                                        media_data=audio_data,
                                        media_type=media_type,
                                        trust_level=s.trust_level,
                                        sequence=s.sequence,
                                        act=s.act,
                                    )
                                    await _emit("audio", audio_seg.model_dump_json())
                            except Exception as e:
                                logger.warning("TTS task failed: %s", e, exc_info=True)
                        tts_tasks.append(asyncio.create_task(_do_tts()))

                    delay = 1.2 if seg.type == "image" else 0.6 if i == 0 else 0.35
                    await asyncio.sleep(delay)

                # Wait for all background TTS to finish before completing stream
                if tts_tasks:
                    await asyncio.gather(*tts_tasks)

                await _emit("status", json.dumps({"status": "complete"}))

            except asyncio.TimeoutError as e:
                logger.warning("[stream] A step timed out: %s", e)
                await _emit("error", json.dumps({
                    "error": "The request took too long. Check your API key and network, then try again."
                }))
            except Exception as e:
                logger.error(f"Narrative generation error: {e}", exc_info=True)
                error_msg = "An unexpected error occurred during narrative generation. Please try again."
                if isinstance(e, ValueError):
                    error_msg = str(e)
                await _emit("error", json.dumps({"error": error_msg}))
            finally:
                session.is_generating = False
                try:
                    session_store.update(session)
                except Exception as store_err:
                    logger.error(f"Failed to update session store in stream finally: {store_err}", exc_info=True)
                await queue.put(None)  # EOF marker

        # Start orchestrator task
        asyncio.create_task(_orchestrator())

        # Yield events from queue as they arrive
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return EventSourceResponse(event_generator())


@router.post("/narrative/{session_id}/followup")
@limiter.limit("10/minute")
async def followup_query(request: Request, session_id: UUID, payload: FollowUpRequest):
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    max_segments_per_session = 50
    if len(session.segments) >= max_segments_per_session:
        raise HTTPException(
            status_code=400,
            detail="This journey has reached its natural conclusion. Please begin a new narrative to explore further."
        )

    question = payload.question

    is_safe = await validate_followup_question(question)
    if not is_safe:
        logger.warning(f"Rejected unsafe/off-topic prompt in session {session_id}: {question}")
        raise HTTPException(
            status_code=400,
            detail="I'm sorry, I can only weave narratives about ancestral heritage, family history, and culture."
        )

    existing_context = "\n".join(
        seg.content for seg in session.segments if seg.type == "text" and seg.content
    )

    grounding = build_grounding_context(session.user_input)
    ui = session.user_input

    prompt = f"""You are Sankofa, continuing a heritage narrative about the {ui.family_name} family
from {ui.region_of_origin} during {ui.time_period}.

=== CULTURAL/HISTORICAL GROUNDING ===
{grounding[:2000]}

=== PREVIOUS NARRATIVE ===
{existing_context[:3000]}

The listener asks: "{question}"

Generate a follow-up narrative segment addressing this question. Maintain the warm,
griot-inspired oral storytelling voice. Generate one relevant watercolor-style image
with warm earth tones and period-appropriate details.
Tag each paragraph with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED]."""

    segments = await generate_interleaved(prompt)
    segments = apply_trust_tags(segments)

    base_seq = len(session.segments)
    for i, seg in enumerate(segments):
        seg.sequence = base_seq + i
        session.segments.append(seg)

    # Generate TTS for follow-up text segments if requested
    audio_segments: list[NarrativeSegment] = []
    if payload.audio:
        for seg in segments:
            if seg.type == "text" and seg.content:
                try:
                    result = await generate_narration(seg.content)
                    if result:
                        audio_data, media_type = result
                        audio_segments.append(NarrativeSegment(
                            type="audio",
                            content=seg.content[:100],
                            media_data=audio_data,
                            media_type=media_type,
                            trust_level=seg.trust_level,
                            sequence=seg.sequence,
                            act=seg.act,
                        ))
                except Exception as e:
                    logger.warning("TTS failed for follow-up segment %s: %s", seg.sequence, e)

    session_store.update(session)
    all_segments = segments + audio_segments
    return {"segments": [seg.model_dump() for seg in all_segments]}


@router.get("/narrative/{session_id}/followup-stream")
@limiter.limit("10/minute")
async def followup_stream(
    request: Request,
    session_id: UUID,
    question: str = Query(..., max_length=2000, description="The follow-up question"),
    audio: bool = Query(default=False, description="Generate TTS audio"),
):
    """SSE-streaming follow-up endpoint — segments arrive one-by-one like the initial narrative."""
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    max_segments_per_session = 50
    if len(session.segments) >= max_segments_per_session:
        raise HTTPException(
            status_code=400,
            detail="This journey has reached its natural conclusion. Please begin a new narrative to explore further.",
        )

    is_safe = await validate_followup_question(question)
    if not is_safe:
        logger.warning("Rejected unsafe/off-topic followup in session %s: %s", session_id, question)
        raise HTTPException(
            status_code=400,
            detail="I'm sorry, I can only weave narratives about ancestral heritage, family history, and culture.",
        )

    async def followup_event_generator():
        logger.info("[followup-stream] ADK follow-up stream for session %s: %s", session_id, question[:80])
        try:
            async for sse_event in run_adk_followup(session, question, audio=audio):
                yield sse_event
        except Exception as e:
            logger.error(f"ADK Followup generation error: {e}", exc_info=True)
            error_msg = "An unexpected error occurred during follow-up generation. Please try again."
            if isinstance(e, ValueError):
                error_msg = str(e)
            yield {"event": "error", "data": json.dumps({"error": error_msg})}

    return EventSourceResponse(followup_event_generator())
