import asyncio
import json
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import NarrativeSegment, FollowUpRequest
from app.store import session_store
from app.rate_limiter import limiter
from app.services.narrative_planner import plan_arc_only, generate_narrative_only, get_fast_arc
from app.services.gemini_service import generate_interleaved
from app.services.trust_classifier import apply_trust_tags
from app.services.tts_service import generate_narration
from app.knowledge.loader import build_grounding_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["narrative"])


@router.get("/narrative/{session_id}/stream")
@limiter.limit("10/minute")
async def stream_narrative(
    request: Request,
    session_id: UUID,
    audio: bool = Query(default=False, description="Generate TTS audio for text segments"),
    fast: bool = Query(default=True, description="Skip arc-planning Gemini call; use template for faster load"),
):
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_generating:
        raise HTTPException(status_code=409, detail="Narrative already generating")

    ARC_PLANNING_TIMEOUT = 60   # seconds (Gemini text call)
    NARRATIVE_TIMEOUT = 120     # seconds (Gemini image + text call)

    async def event_generator():
        session.is_generating = True
        session_store.update(session)
        queue = asyncio.Queue()

        async def _emit(event_name: str, data: str):
            await queue.put({"event": event_name, "data": data})

        async def _orchestrator():
            try:
                logger.info("[stream] Narrative stream started for session %s (fast=%s, audio=%s)", str(session_id), fast, audio)
                await _emit("status", json.dumps({"status": "generating"}))

                if fast:
                    await _emit("status", json.dumps({"status": "generating_narrative"}))
                    logger.info("[stream] Step: generating_narrative (fast mode, no arc call)")
                    arc, grounding_context = get_fast_arc(session)
                    await _emit("arc", json.dumps(arc))
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=NARRATIVE_TIMEOUT,
                    )
                else:
                    await _emit("status", json.dumps({"status": "planning_arc"}))
                    logger.info("[stream] Step: planning_arc (timeout %ss)", ARC_PLANNING_TIMEOUT)
                    arc_outline, grounding_context = await asyncio.wait_for(
                        plan_arc_only(session),
                        timeout=ARC_PLANNING_TIMEOUT,
                    )
                    await _emit("arc", json.dumps(arc_outline))

                    await _emit("status", json.dumps({"status": "generating_narrative"}))
                    logger.info("[stream] Step: generating_narrative (timeout %ss)", NARRATIVE_TIMEOUT)
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=NARRATIVE_TIMEOUT,
                    )
                logger.info("[stream] Generated %s segments, streaming to client", len(segments))

                # Steam segments immediately to queue, kick off TTS tasks in background
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
                await _emit("error", json.dumps({"error": str(e)}))
            finally:
                session.is_generating = False
                session_store.update(session)
                await queue.put(None)  # EOF marker

        # Start orchestrator task
        orchestrator_task = asyncio.create_task(_orchestrator())

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

    question = payload.question

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
