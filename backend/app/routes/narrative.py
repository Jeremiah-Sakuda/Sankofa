import asyncio
import json
import logging
import time
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from app.knowledge.loader import build_grounding_context
from app.models.schemas import FollowUpRequest, NarrativeSegment
from app.models.user import User
from app.rate_limiter import generation_limiter, limiter
from app.routes.auth import require_user
from app.services.adk_orchestrator import (
    run_adk_followup,
    run_adk_narrative,
    run_adk_narrative_with_review,
    run_critic_review,
)
from app.services.analytics import EventType, track_event
from app.services.gemini_service import generate_interleaved, validate_followup_question
from app.services.narrative_planner import generate_narrative_only, get_fast_arc, plan_arc_only
from app.services.trust_classifier import apply_trust_tags
from app.services.tts_service import generate_narration, spawn_tts_task
from app.store import session_store
from app.utils.sanitization import sanitize_input

# Load sample narrative - always fresh read to pick up changes
_SAMPLE_NARRATIVE_PATH = Path(__file__).parent.parent / "data" / "sample_narrative.json"

def _load_sample_narrative() -> dict:
    """Load sample narrative from JSON file. Always reads fresh for reliability."""
    with open(_SAMPLE_NARRATIVE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["narrative"])


@router.get("/narrative/sample")
@limiter.limit("30/minute")
async def get_sample_narrative(request: Request):
    """Return pre-generated sample narrative for "See an example" feature.

    Returns the full narrative data including arc outline and all segments.
    This is read-only and does not create a session.
    """
    sample = _load_sample_narrative()
    return {
        "session_id": sample["session_id"],
        "user_input": sample["user_input"],
        "arc_outline": sample["arc_outline"],
        "segments": sample["segments"],
    }


@router.get("/narrative/sample/stream")
@limiter.limit("30/minute")
async def stream_sample_narrative(request: Request):
    """Stream pre-generated sample narrative via SSE for consistent UX.

    Streams the sample narrative with realistic delays to match the
    live generation experience.
    """
    sample = _load_sample_narrative()

    async def sample_event_generator():
        yield {"event": "status", "data": json.dumps({"status": "generating"})}
        await asyncio.sleep(0.3)

        # Emit arc
        yield {"event": "arc", "data": json.dumps(sample["arc_outline"])}
        await asyncio.sleep(0.5)

        yield {"event": "status", "data": json.dumps({"status": "generating_narrative"})}

        # Stream segments with natural pacing
        for i, seg in enumerate(sample["segments"]):
            yield {"event": seg["type"], "data": json.dumps(seg)}
            delay = _DELAY_IMAGE if seg["type"] == "image" else (_DELAY_FIRST_TEXT if i == 0 else _DELAY_TEXT)
            await asyncio.sleep(delay)

        yield {"event": "status", "data": json.dumps({"status": "complete"})}

    return EventSourceResponse(sample_event_generator())

# Context window limits for prompt truncation (characters)
_CTX_GROUNDING = 2000
_CTX_EXISTING = 3000

# Streaming delays (seconds) for natural pacing
_DELAY_IMAGE = 1.2
_DELAY_FIRST_TEXT = 0.6
_DELAY_TEXT = 0.35

# Overall timeout for narrative generation (seconds)
# Prevents hung streams from consuming resources indefinitely
# Set to 7 minutes to accommodate image generation + TTS (Gemini can be slow)
_OVERALL_TIMEOUT = 420


@router.get("/narrative/{session_id}/stream")
@limiter.limit("10/minute")
async def stream_narrative(
    request: Request,
    session_id: UUID,
    audio: bool = Query(default=False, description="Generate TTS audio for text segments"),
    fast: bool = Query(default=True, description="Skip arc-planning Gemini call; use template for faster load"),
    use_adk: bool = Query(default=True, description="Route through the ADK agent orchestrator"),
    review: bool = Query(default=False, description="Enable critic agent review for quality assurance"),
):
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_generating and not session.is_generating_stale:
        raise HTTPException(status_code=409, detail="Narrative already generating")
    if session.is_generating_stale:
        logger.warning("[stream] Clearing stale is_generating flag for session %s", str(session_id))
        session.is_generating = False
        session_store.update(session)

    # Check concurrent generation limit per IP
    client_ip = get_remote_address(request)
    if not generation_limiter.can_start(client_ip, str(session_id)):
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent narrative generations. Please wait for your current story to complete."
        )

    # --- ADK-orchestrated path ---
    if use_adk:
        async def adk_event_generator():
            # Track this generation in the concurrency limiter
            if not generation_limiter.start(client_ip, str(session_id)):
                yield {"event": "error", "data": json.dumps({"error": "Too many concurrent generations"})}
                return

            session.is_generating = True
            session.generating_started_at = time.time()
            session_store.update(session)
            start_time = time.time()
            timed_out = False
            completed = False
            had_error = False

            # Track narrative start
            await track_event(
                EventType.NARRATIVE_START,
                str(session_id),
                region=session.user_input.region_of_origin,
                metadata={"audio_enabled": audio}
            )

            try:
                # Choose between standard or critic-reviewed generation
                if review:
                    logger.info("[stream] ADK narrative stream with critic review started for session %s (audio=%s)", str(session_id), audio)
                    adk_generator = run_adk_narrative_with_review(session, audio=audio)
                else:
                    logger.info("[stream] ADK narrative stream started for session %s (audio=%s)", str(session_id), audio)
                    adk_generator = run_adk_narrative(session, audio=audio)

                async for sse_event in adk_generator:
                    # Check overall timeout
                    if time.time() - start_time > _OVERALL_TIMEOUT:
                        logger.warning("[stream] Overall timeout (%ds) exceeded for session %s", _OVERALL_TIMEOUT, str(session_id))
                        timed_out = True
                        had_error = True
                        yield {"event": "error", "data": json.dumps({
                            "error": "The story is taking longer than expected. Please try again."
                        })}
                        break
                    # Check for completion status event
                    if sse_event.get("event") == "status":
                        try:
                            status_data = json.loads(sse_event.get("data", "{}"))
                            if status_data.get("status") == "complete":
                                completed = True
                        except json.JSONDecodeError:
                            pass
                    yield sse_event
            except asyncio.TimeoutError:
                logger.warning("[stream] Timeout for session %s", str(session_id))
                had_error = True
                yield {"event": "error", "data": json.dumps({
                    "error": "The story is taking longer than expected. Please try again."
                })}
            except Exception as e:
                logger.error(f"ADK Narrative generation error: {e}", exc_info=True)
                had_error = True
                error_msg = "An unexpected error occurred during narrative generation. Please try again."
                if isinstance(e, ValueError):
                    error_msg = str(e)
                yield {"event": "error", "data": json.dumps({"error": error_msg})}
            finally:
                generation_limiter.finish(client_ip, str(session_id))
                session.is_generating = False
                duration = int(time.time() - start_time)

                # Track completion or error
                if completed:
                    await track_event(
                        EventType.NARRATIVE_COMPLETE,
                        str(session_id),
                        region=session.user_input.region_of_origin,
                        metadata={"segment_count": len(session.segments), "duration_seconds": duration}
                    )
                elif had_error:
                    await track_event(
                        EventType.NARRATIVE_ERROR,
                        str(session_id),
                        metadata={"error_type": "timeout" if timed_out else "exception"}
                    )

                if timed_out:
                    logger.info("[stream] Session %s timed out after %ds", str(session_id), duration)
                try:
                    session_store.update(session)
                except Exception as store_err:
                    logger.error(f"Failed to update session store in stream finally: {store_err}", exc_info=True)

        return EventSourceResponse(adk_event_generator())

    # --- Direct pipeline fallback (use_adk=false) ---
    arc_planning_timeout = 60   # seconds (Gemini text call)
    narrative_timeout = 120     # seconds (Gemini image + text call)

    async def event_generator():
        # Track this generation in the concurrency limiter
        if not generation_limiter.start(client_ip, str(session_id)):
            yield {"event": "error", "data": json.dumps({"error": "Too many concurrent generations"})}
            return

        session.is_generating = True
        session.generating_started_at = time.time()
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
                tts_queue: asyncio.Queue = asyncio.Queue()
                for i, seg in enumerate(segments):
                    session.segments.append(seg)
                    await _emit(seg.type, seg.model_dump_json())

                    if audio and seg.type == "text" and seg.content and not seg.media_data:
                        tts_tasks.append(spawn_tts_task(seg, tts_queue))

                    delay = _DELAY_IMAGE if seg.type == "image" else _DELAY_FIRST_TEXT if i == 0 else _DELAY_TEXT
                    await asyncio.sleep(delay)

                # Wait for all background TTS to finish, then emit in sequence order
                if tts_tasks:
                    await asyncio.gather(*tts_tasks)
                    audio_segments: list = []
                    while not tts_queue.empty():
                        audio_segments.append(await tts_queue.get())
                    audio_segments.sort(key=lambda s: s.sequence)
                    for audio_seg in audio_segments:
                        await _emit("audio", audio_seg.model_dump_json())

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
                generation_limiter.finish(client_ip, str(session_id))
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


@router.post("/narrative/{session_id}/review")
@limiter.limit("5/minute")
async def review_narrative(request: Request, session_id: UUID):
    """Run the critic agent to review an existing narrative.

    This endpoint allows quality review of a previously generated narrative
    without regenerating it. Useful for:
    - Quality assurance checks
    - Understanding why a narrative might need improvement
    - Getting specific feedback for manual review

    Returns:
        Review results including quality score, authenticity assessment,
        and actionable improvement suggestions.
    """
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.segments:
        raise HTTPException(status_code=400, detail="No narrative segments to review")

    logger.info("[review] Running critic review for session %s", str(session_id))

    arc_json = json.dumps(session.arc_outline) if session.arc_outline else None
    review = await run_critic_review(session, arc_json)

    return {
        "session_id": str(session_id),
        "review": {
            "passed": review["overall_passed"],
            "overall_score": review["overall_score"],
            "quality": review["quality_review"],
            "authenticity": review["authenticity_review"],
            "improvements": review["improvements"],
        }
    }


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

    # Sanitize the question to prevent prompt injection
    question = sanitize_input(payload.question, "followup_question") or ""

    is_safe = await validate_followup_question(question)
    if not is_safe:
        # Log rejection without PII (question content)
        logger.warning("Rejected unsafe/off-topic prompt in session %s", session_id)
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
{grounding[:_CTX_GROUNDING]}

=== PREVIOUS NARRATIVE ===
{existing_context[:_CTX_EXISTING]}

The listener asks: "{question}"

Generate a follow-up narrative segment addressing this question. Maintain the warm,
griot-inspired oral storytelling voice.

IMAGE STYLE (mandatory for every image):
Paint in a WATERCOLOR illustration style — visible brushstrokes, soft wet-on-wet
edges, transparent washes of pigment with white paper showing through. Use a warm
palette of burnt sienna, raw umber, yellow ochre, and gold leaf accents. No
photorealism, no digital art, no sharp vector edges. Every image must look like a
hand-painted watercolor on textured paper. Period-appropriate details only.

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

    # Track follow-up usage
    await track_event(
        EventType.FOLLOWUP_USED,
        str(session_id),
        region=session.user_input.region_of_origin,
        metadata={"segment_count": len(segments)}
    )

    all_segments = segments + audio_segments
    return {"segments": [seg.model_dump() for seg in all_segments]}


class FollowUpStreamRequest(BaseModel):
    """Request body for follow-up streaming (POST to keep PII out of logs)."""
    question: str = Field(..., max_length=2000, description="The follow-up question")
    audio: bool = Field(default=False, description="Generate TTS audio")


@router.post("/narrative/{session_id}/followup-stream")
@limiter.limit("10/minute")
async def followup_stream(
    request: Request,
    session_id: UUID,
    body: FollowUpStreamRequest,
):
    """SSE-streaming follow-up endpoint — segments arrive one-by-one like the initial narrative.

    Uses POST to keep user questions out of server logs (PII protection).
    """
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    max_segments_per_session = 50
    if len(session.segments) >= max_segments_per_session:
        raise HTTPException(
            status_code=400,
            detail="This journey has reached its natural conclusion. Please begin a new narrative to explore further.",
        )

    # Sanitize the question to prevent prompt injection
    sanitized_question = sanitize_input(body.question, "followup_question") or ""

    is_safe = await validate_followup_question(sanitized_question)
    if not is_safe:
        # Log only that rejection happened, not the actual content (PII)
        logger.warning("Rejected unsafe/off-topic followup in session %s", session_id)
        raise HTTPException(
            status_code=400,
            detail="I'm sorry, I can only weave narratives about ancestral heritage, family history, and culture.",
        )

    async def followup_event_generator():
        # Log session ID but not question content (PII protection)
        logger.info("[followup-stream] ADK follow-up stream for session %s", session_id)
        try:
            async for sse_event in run_adk_followup(session, sanitized_question, audio=body.audio):
                yield sse_event
        except Exception as e:
            logger.error("ADK Followup generation error: %s", type(e).__name__, exc_info=True)
            error_msg = "An unexpected error occurred during follow-up generation. Please try again."
            if isinstance(e, ValueError):
                error_msg = str(e)
            yield {"event": "error", "data": json.dumps({"error": error_msg})}

    return EventSourceResponse(followup_event_generator())


# ---------------------------------------------------------------------------
# Library endpoints (user's saved narratives)
# ---------------------------------------------------------------------------

class NarrativeSummary:
    """Summary of a narrative for library listing."""
    def __init__(
        self,
        session_id: str,
        family_name: str,
        region: str,
        era: str,
        created_at: float,
        segment_count: int,
        first_image_data: str | None = None,
        arc_title: str | None = None,
    ):
        self.session_id = session_id
        self.family_name = family_name
        self.region = region
        self.era = era
        self.created_at = created_at
        self.segment_count = segment_count
        self.first_image_data = first_image_data
        self.arc_title = arc_title


@router.get("/narratives")
async def list_narratives(
    request: Request,
    user: User = Depends(require_user),
    limit: int = Query(default=20, le=50),
):
    """List user's saved narratives for the library."""
    sessions = session_store.list_by_owner(user.user_id, limit=limit)

    narratives = []
    for session in sessions:
        # Find first image for thumbnail
        first_image = next(
            (s for s in session.segments if s.type == "image" and s.media_data),
            None
        )

        # Get arc title if available
        arc_title = None
        if session.arc_outline and isinstance(session.arc_outline, dict):
            arc_title = session.arc_outline.get("title")

        narratives.append({
            "session_id": session.session_id,
            "family_name": session.user_input.family_name,
            "region": session.user_input.region_of_origin,
            "era": session.user_input.time_period,
            "created_at": session.created_at,
            "segment_count": len(session.segments),
            "first_image_data": first_image.media_data if first_image else None,
            "first_image_type": first_image.media_type if first_image else None,
            "arc_title": arc_title,
        })

    return {"narratives": narratives}


@router.get("/narratives/{session_id}")
async def get_narrative(
    request: Request,
    session_id: UUID,
    user: User = Depends(require_user),
):
    """Get a full narrative for replay. User must own the narrative."""
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Check ownership
    if session.owner_id != user.user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this narrative")

    return {
        "session_id": session.session_id,
        "user_input": session.user_input.model_dump(),
        "arc_outline": session.arc_outline,
        "segments": [seg.model_dump() for seg in session.segments],
        "created_at": session.created_at,
    }


@router.post("/narratives/{session_id}/claim")
async def claim_narrative(
    request: Request,
    session_id: UUID,
    user: User = Depends(require_user),
):
    """Claim an unclaimed narrative (associate it with the current user)."""
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Can only claim unclaimed narratives
    if session.owner_id and session.owner_id != user.user_id:
        raise HTTPException(status_code=403, detail="This narrative belongs to another user")

    # Set owner
    if session_store.set_owner(str(session_id), user.user_id):
        return {"message": "Narrative saved to your library"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save narrative")
