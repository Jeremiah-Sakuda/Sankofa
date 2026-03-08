import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import NarrativeSegment, FollowUpRequest
from app.models.session import session_store
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
            logger.info("[stream] Narrative stream started for session %s (fast=%s)", session_id, fast)
            yield {"event": "status", "data": json.dumps({"status": "generating"})}

            try:
                if fast:
                    # Skip arc-planning Gemini call; use template arc for much faster start
                    yield {"event": "status", "data": json.dumps({"status": "generating_narrative"})}
                    logger.info("[stream] Step: generating_narrative (fast mode, no arc call)")
                    _, grounding_context = get_fast_arc(session)
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

                    yield {"event": "status", "data": json.dumps({"status": "generating_narrative"})}
                    logger.info("[stream] Step: generating_narrative (timeout %ss)", NARRATIVE_TIMEOUT)
                    segments = await asyncio.wait_for(
                        generate_narrative_only(session, grounding_context),
                        timeout=NARRATIVE_TIMEOUT,
                    )
                logger.info("[stream] Generated %s segments, streaming to client", len(segments))
            except asyncio.TimeoutError as e:
                # asyncio.wait_for doesn't tell us which call timed out; log and give a generic message
                logger.warning("[stream] A step timed out: %s", e)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "The request took too long. Check your API key and network, then try again.",
                    }),
                }
                return

            for seg in segments:
                session.segments.append(seg)
                yield {
                    "event": seg.type,
                    "data": seg.model_dump_json(),
                }
                await asyncio.sleep(0.5)

            # After all segments are streamed, generate TTS audio if requested
            if audio:
                yield {"event": "status", "data": json.dumps({"status": "generating_audio"})}
                logger.info("[stream] Generating TTS for %s text segments", sum(1 for s in session.segments if s.type == "text" and s.content))
                for seg in session.segments:
                    if seg.type == "text" and seg.content and not seg.media_data:
                        try:
                            result = await generate_narration(seg.content)
                            if result:
                                audio_data, media_type = result
                                audio_seg = NarrativeSegment(
                                    type="audio",
                                    content=seg.content[:100],
                                    media_data=audio_data,
                                    media_type=media_type,
                                    trust_level=seg.trust_level,
                                    sequence=seg.sequence,
                                    act=seg.act,
                                )
                                yield {
                                    "event": "audio",
                                    "data": audio_seg.model_dump_json(),
                                }
                                await asyncio.sleep(0.3)
                            else:
                                logger.warning("TTS returned no audio for segment %s", seg.sequence)
                        except Exception as e:
                            logger.warning("TTS failed for segment %s: %s", seg.sequence, e, exc_info=True)

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
