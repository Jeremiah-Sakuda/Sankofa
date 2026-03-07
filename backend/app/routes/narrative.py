import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import NarrativeSegment, FollowUpRequest
from app.models.session import session_store
from app.services.narrative_planner import plan_and_generate
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
):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_generating:
        raise HTTPException(status_code=409, detail="Narrative already generating")

    async def event_generator():
        session.is_generating = True
        session_store.update(session)

        try:
            yield {"event": "status", "data": json.dumps({"status": "generating"})}

            segments = await plan_and_generate(session)

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
                for seg in session.segments:
                    if seg.type == "text" and seg.content and not seg.media_data:
                        try:
                            audio_data = await generate_narration(seg.content)
                            if audio_data:
                                audio_seg = NarrativeSegment(
                                    type="audio",
                                    content=seg.content[:100],
                                    media_data=audio_data,
                                    media_type="audio/wav",
                                    trust_level=seg.trust_level,
                                    sequence=seg.sequence,
                                    act=seg.act,
                                )
                                yield {
                                    "event": "audio",
                                    "data": audio_seg.model_dump_json(),
                                }
                                await asyncio.sleep(0.3)
                        except Exception as e:
                            logger.warning(f"TTS failed for segment {seg.sequence}: {e}")

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
