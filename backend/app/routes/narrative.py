import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import NarrativeSegment, FollowUpRequest
from app.store import session_store
from app.services.narrative_planner import plan_arc_only, generate_narrative_only, get_fast_arc
from app.services.gemini_service import generate_interleaved
from app.services.trust_classifier import apply_trust_tags
from app.services.tts_service import generate_narration
from app.knowledge.loader import build_grounding_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["narrative"])


@router.get("/narrative/{session_id}/stream")
async def stream_narrative(
    session_id: str,
    audio: bool = Query(default=False, description="Generate TTS audio for text segments"),
    fast: bool = Query(default=True, description="Skip arc-planning Gemini call; use template for faster load"),
):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_generating:
        raise HTTPException(status_code=409, detail="Narrative already generating")

    ARC_PLANNING_TIMEOUT = 60   # seconds (Gemini text call)
    NARRATIVE_TIMEOUT = 120     # seconds (Gemini image + text call)

    async def event_generator():
        session.is_generating = True
        session_store.update(session)

        try:
            logger.info("[stream] Narrative stream started for session %s (fast=%s, audio=%s)", session_id, fast, audio)
            yield {"event": "status", "data": json.dumps({"status": "generating"})}

            try:
                if fast:
                    yield {"event": "status", "data": json.dumps({"status": "generating_narrative"})}
                    logger.info("[stream] Step: generating_narrative (fast mode, no arc call)")
                    arc, grounding_context = get_fast_arc(session)
                    yield {"event": "arc", "data": json.dumps(arc)}
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=NARRATIVE_TIMEOUT,
                    )
                else:
                    yield {"event": "status", "data": json.dumps({"status": "planning_arc"})}
                    logger.info("[stream] Step: planning_arc (timeout %ss)", ARC_PLANNING_TIMEOUT)
                    arc_outline, grounding_context = await asyncio.wait_for(
                        plan_arc_only(session),
                        timeout=ARC_PLANNING_TIMEOUT,
                    )
                    yield {"event": "arc", "data": json.dumps(arc_outline)}

                    yield {"event": "status", "data": json.dumps({"status": "generating_narrative"})}
                    logger.info("[stream] Step: generating_narrative (timeout %ss)", NARRATIVE_TIMEOUT)
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=NARRATIVE_TIMEOUT,
                    )
                logger.info("[stream] Generated %s segments, streaming to client", len(segments))
            except asyncio.TimeoutError as e:
                logger.warning("[stream] A step timed out: %s", e)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "The request took too long. Check your API key and network, then try again.",
                    }),
                }
                return

            # Stream segments with interleaved audio generation.
            # For each text segment: emit the text event, kick off TTS
            # concurrently, then emit the audio event right after.
            pending_tts: asyncio.Task | None = None

            for i, seg in enumerate(segments):
                session.segments.append(seg)

                # If there's a pending TTS task from the previous text segment,
                # await it now and emit the audio event before moving on.
                if pending_tts is not None:
                    tts_seg, tts_result = await pending_tts
                    pending_tts = None
                    if tts_result is not None:
                        audio_data, media_type = tts_result
                        audio_seg = NarrativeSegment(
                            type="audio",
                            content=tts_seg.content[:100] if tts_seg.content else "",
                            media_data=audio_data,
                            media_type=media_type,
                            trust_level=tts_seg.trust_level,
                            sequence=tts_seg.sequence,
                            act=tts_seg.act,
                        )
                        yield {
                            "event": "audio",
                            "data": audio_seg.model_dump_json(),
                        }

                # Emit the current segment
                yield {
                    "event": seg.type,
                    "data": seg.model_dump_json(),
                }

                # Kick off TTS for this text segment in the background
                if audio and seg.type == "text" and seg.content and not seg.media_data:
                    async def _do_tts(s=seg):
                        result = await generate_narration(s.content)
                        return (s, result)
                    pending_tts = asyncio.create_task(_do_tts())

                # Stagger delay (shorter now since TTS runs concurrently)
                delay = 1.2 if seg.type == "image" else 0.6 if i == 0 else 0.35
                await asyncio.sleep(delay)

            # Flush the last pending TTS result
            if pending_tts is not None:
                try:
                    tts_seg, tts_result = await pending_tts
                    if tts_result is not None:
                        audio_data, media_type = tts_result
                        audio_seg = NarrativeSegment(
                            type="audio",
                            content=tts_seg.content[:100] if tts_seg.content else "",
                            media_data=audio_data,
                            media_type=media_type,
                            trust_level=tts_seg.trust_level,
                            sequence=tts_seg.sequence,
                            act=tts_seg.act,
                        )
                        yield {
                            "event": "audio",
                            "data": audio_seg.model_dump_json(),
                        }
                except Exception as e:
                    logger.warning("Final TTS task failed: %s", e, exc_info=True)

            yield {"event": "status", "data": json.dumps({"status": "complete"})}

        except Exception as e:
            logger.error(f"Narrative generation error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }
        finally:
            session.is_generating = False
            session_store.update(session)

    return EventSourceResponse(event_generator())


@router.post("/narrative/{session_id}/followup")
async def followup_query(session_id: str, request: FollowUpRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = request.question

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

    session_store.update(session)
    return {"segments": [seg.model_dump() for seg in segments]}
