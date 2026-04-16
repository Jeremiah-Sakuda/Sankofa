"""
ADK Orchestrator — Bridges the Sankofa ADK agent with SSE event streaming.

Invokes sankofa_agent via the ADK Runner, observes tool calls and results,
and yields SSE-compatible events that the frontend already expects.

Usage:
    async for sse_event in run_adk_narrative(session, audio=True):
        yield sse_event   # {"event": "text", "data": "..."}
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from app.models.schemas import NarrativeSegment
from app.models.session import Session
from app.services.adk_agent import (
    media_store,
    sankofa_agent,
    sankofa_critic_agent,
    review_narrative_quality,
    review_cultural_authenticity,
    suggest_narrative_improvements,
)
from app.services.tts_service import spawn_tts_task
from app.store import session_store
from app.utils.error_messages import translate_error_for_sse

logger = logging.getLogger(__name__)

# Streaming delays (seconds) for natural pacing
_DELAY_IMAGE = 1.2
_DELAY_FIRST_TEXT = 0.6
_DELAY_TEXT = 0.35

# ---------------------------------------------------------------------------
# ADK Runner setup (separate from the app's session store)
# ---------------------------------------------------------------------------

_adk_session_service = InMemorySessionService()
_runner = Runner(
    agent=sankofa_agent,
    app_name="sankofa",
    session_service=_adk_session_service,
)

# Critic agent runner for narrative review
_critic_session_service = InMemorySessionService()
_critic_runner = Runner(
    agent=sankofa_critic_agent,
    app_name="sankofa_critic",
    session_service=_critic_session_service,
)

# ---------------------------------------------------------------------------
# "Thinking aloud" messages — shown to the user as the agent works
# ---------------------------------------------------------------------------

_THINKING_MESSAGES = {
    "lookup_cultural_context": "Consulting the knowledge base on {region} heritage...",
    "assess_context_quality": "Evaluating available historical records...",
    "research_region_history": "Searching for additional context on {region} during {time_period}...",
    "plan_narrative_arc": "Planning a three-act arc for the {family_name} family story...",
    "generate_act_segments": "Weaving Act {act_number} of the narrative...",
    "enrich_segment": "Enriching the narrative with deeper historical detail...",
}


def _thinking_msg(tool_name: str, args: dict) -> str | None:
    """Format a thinking-aloud message for a tool call, or None if unmapped."""
    template = _THINKING_MESSAGES.get(tool_name)
    if not template:
        return None
    try:
        return template.format(**args)
    except KeyError:
        # Strip the first placeholder and return a safe prefix
        return template.split("{")[0].rstrip(" .") + "..."


def _parse_json_safe(raw: str) -> dict | list | None:
    """Parse JSON from a raw string, stripping markdown code fences if present."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        cleaned = cleaned.rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None


def _sse(event: str, **kwargs) -> dict:
    """Build an SSE-compatible dict."""
    return {"event": event, "data": json.dumps(kwargs)}


def _sse_status(status: str, **extra) -> dict:
    return {"event": "status", "data": json.dumps({"status": status, **extra})}


async def _drain_tts_queue(tts_queue: asyncio.Queue) -> list[NarrativeSegment]:
    """Non-blockingly drain all completed TTS results, returned sorted by sequence."""
    audio_segments: list[NarrativeSegment] = []
    while not tts_queue.empty():
        try:
            audio_segments.append(tts_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    audio_segments.sort(key=lambda s: s.sequence)
    return audio_segments


# ---------------------------------------------------------------------------
# Main narrative generation via ADK
# ---------------------------------------------------------------------------

async def run_adk_narrative(
    session: Session,
    audio: bool = False,
) -> AsyncGenerator[dict, None]:
    """Run the ADK agent for initial narrative generation, yielding SSE events.

    The agent follows its instruction workflow:
      lookup_cultural_context -> assess_context_quality -> (research if sparse)
      -> plan_narrative_arc -> generate_act_segments x3

    The orchestrator intercepts each step and emits the appropriate SSE events
    that the frontend already understands (arc, text, image, audio, status).
    """
    ui = session.user_input

    # Create a fresh ADK session
    adk_session = await _adk_session_service.create_session(
        app_name="sankofa",
        user_id=session.session_id,
    )

    # Build initial prompt — tell the agent to skip TTS (orchestrator handles it)
    prompt_lines = [
        f"Tell the heritage story of the {ui.family_name} family "
        f"from {ui.region_of_origin} during {ui.time_period}.",
    ]
    if ui.known_fragments:
        prompt_lines.append(f"Known family details: {ui.known_fragments}")
    if ui.language_or_ethnicity:
        prompt_lines.append(f"Language/ethnicity: {ui.language_or_ethnicity}")
    if ui.specific_interests:
        prompt_lines.append(f"Areas of interest: {ui.specific_interests}")
    prompt_lines.append(
        "Do NOT call generate_audio_narration — audio will be handled separately."
    )

    user_message = Content(
        role="user",
        parts=[Part(text="\n".join(prompt_lines))],
    )

    yield _sse_status("generating")

    # State tracking
    arc_emitted = False
    total_segments: list[NarrativeSegment] = []
    hero_assigned = False
    tts_tasks: list[asyncio.Task] = []
    tts_queue: asyncio.Queue = asyncio.Queue()

    # Track the act_number from generate_act_segments calls
    current_act: int | None = None

    try:
        async for event in _runner.run_async(
            user_id=session.session_id,
            session_id=adk_session.id,
            new_message=user_message,
        ):
            if not event.content or not event.content.parts:
                continue

            for part in event.content.parts:

                # ----- Tool call: emit "thinking aloud" status -----
                if part.function_call:
                    fc = part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}

                    # notify_user is a special case — surface its message
                    if tool_name == "notify_user":
                        msg = tool_args.get("message", "")
                        if msg:
                            yield _sse_status("agent_message", message=msg)
                        continue

                    # Track act number for segment processing
                    if tool_name == "generate_act_segments":
                        current_act = int(tool_args.get("act_number", 1))

                    # Emit thinking-aloud message
                    thinking = _thinking_msg(tool_name, tool_args)
                    if thinking:
                        yield _sse_status("thinking", message=thinking)

                    # Emit canonical progress steps the frontend recognizes
                    if tool_name == "plan_narrative_arc":
                        yield _sse_status("planning_arc")
                    elif tool_name == "generate_act_segments":
                        yield _sse_status("generating_narrative")

                # ----- Tool result: extract data and emit SSE events -----
                if part.function_response:
                    fr = part.function_response
                    tool_name = fr.name
                    result_str = ""
                    if fr.response:
                        # ADK wraps tool return values in {"result": "..."}
                        result_str = str(fr.response.get("result", ""))

                    # --- plan_narrative_arc → emit arc ---
                    if tool_name == "plan_narrative_arc" and not arc_emitted:
                        arc = _parse_json_safe(result_str)
                        if isinstance(arc, dict):
                            session.arc_outline = arc
                            yield {"event": "arc", "data": json.dumps(arc)}
                            arc_emitted = True
                        else:
                            logger.warning(
                                "[adk-orch] Could not parse arc from plan_narrative_arc result"
                            )

                    # --- generate_act_segments → emit segments one by one ---
                    elif tool_name == "generate_act_segments":
                        segments_data = _parse_json_safe(result_str)
                        if isinstance(segments_data, list):
                            for i, seg_data in enumerate(segments_data):
                                seg = NarrativeSegment(
                                    type=seg_data.get("type", "text"),
                                    content=seg_data.get("content"),
                                    media_data=media_store.pop(seg_data["media_reference"], None) if
                                               seg_data.get("media_reference") else seg_data.get("media_data"),
                                    media_type=seg_data.get("media_type"),
                                    trust_level=seg_data.get("trust_level", "reconstructed"),
                                    sequence=len(total_segments),
                                    act=current_act or seg_data.get("act"),
                                    is_hero=False,
                                )

                                # First image overall is the hero
                                if seg.type == "image" and not hero_assigned:
                                    seg.is_hero = True
                                    hero_assigned = True

                                total_segments.append(seg)
                                session.segments.append(seg)
                                yield {"event": seg.type, "data": seg.model_dump_json()}

                                # Spawn TTS in background for text segments
                                if (
                                    audio
                                    and seg.type == "text"
                                    and seg.content
                                    and not seg.media_data
                                ):
                                    tts_tasks.append(spawn_tts_task(seg, tts_queue))

                                # Stagger delivery for natural feel
                                delay = _DELAY_IMAGE if seg.type == "image" else (_DELAY_FIRST_TEXT if i == 0 else _DELAY_TEXT)
                                await asyncio.sleep(delay)

                            # Drain any TTS that finished while we were emitting text/images
                            for audio_seg in await _drain_tts_queue(tts_queue):
                                yield {"event": "audio", "data": audio_seg.model_dump_json()}
                        else:
                            logger.warning(
                                "[adk-orch] Could not parse segments from generate_act_segments"
                            )

        # --- Collect any remaining TTS results and yield in sequence order ---
        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)
            for audio_seg in await _drain_tts_queue(tts_queue):
                yield {"event": "audio", "data": audio_seg.model_dump_json()}

        # Persist session
        session_store.update(session)

        yield _sse_status("complete")

    except Exception as e:
        logger.error("[adk-orch] Narrative generation error: %s", e, exc_info=True)
        yield {"event": "error", "data": json.dumps(translate_error_for_sse(e))}


# ---------------------------------------------------------------------------
# Follow-up generation via ADK
# ---------------------------------------------------------------------------

async def run_adk_followup(
    session: Session,
    question: str,
    audio: bool = False,
) -> AsyncGenerator[dict, None]:
    """Run the ADK agent for a follow-up question, yielding SSE events.

    The agent uses recall_narrative_context to review the story so far,
    then deep_dive to generate a focused mini-narrative on the topic.
    """
    adk_session = await _adk_session_service.create_session(
        app_name="sankofa",
        user_id=session.session_id,
    )

    ui = session.user_input
    prompt = (
        f"The listener is exploring the heritage story of the {ui.family_name} family "
        f"from {ui.region_of_origin} during {ui.time_period}.\n"
        f"Their session_id is '{session.session_id}'.\n"
        f"They ask: \"{question}\"\n\n"
        f"Use recall_narrative_context to review what was already told, "
        f"then use deep_dive to explore this question.\n"
        f"Do NOT call generate_audio_narration — audio will be handled separately."
    )

    user_message = Content(
        role="user",
        parts=[Part(text=prompt)],
    )

    yield _sse_status("generating")

    tts_tasks: list[asyncio.Task] = []
    tts_queue: asyncio.Queue = asyncio.Queue()

    try:
        async for event in _runner.run_async(
            user_id=session.session_id,
            session_id=adk_session.id,
            new_message=user_message,
        ):
            if not event.content or not event.content.parts:
                continue

            for part in event.content.parts:

                if part.function_call:
                    fc = part.function_call
                    if fc.name == "recall_narrative_context":
                        yield _sse_status("thinking", message="Recalling your story so far...")
                    elif fc.name == "deep_dive":
                        topic = (dict(fc.args) if fc.args else {}).get("topic", question)
                        yield _sse_status("thinking", message=f"Exploring deeper: {topic}...")
                        yield _sse_status("generating_narrative")

                if part.function_response:
                    fr = part.function_response
                    if fr.name == "deep_dive":
                        result_str = str(fr.response.get("result", "")) if fr.response else ""
                        segments_data = _parse_json_safe(result_str)
                        if isinstance(segments_data, list):
                            for seg_data in segments_data:
                                seg = NarrativeSegment(
                                    type=seg_data.get("type", "text"),
                                    content=seg_data.get("content"),
                                    media_data=media_store.pop(seg_data["media_reference"], None) if
                                               seg_data.get("media_reference") else seg_data.get("media_data"),
                                    media_type=seg_data.get("media_type"),
                                    trust_level=seg_data.get("trust_level", "reconstructed"),
                                    sequence=len(session.segments),
                                    act=seg_data.get("act"),
                                )
                                session.segments.append(seg)
                                yield {"event": seg.type, "data": seg.model_dump_json()}

                                if audio and seg.type == "text" and seg.content:
                                    tts_tasks.append(spawn_tts_task(seg, tts_queue))

                                await asyncio.sleep(_DELAY_TEXT)

                            # Drain any TTS that finished during segment emission
                            for audio_seg in await _drain_tts_queue(tts_queue):
                                yield {"event": "audio", "data": audio_seg.model_dump_json()}

        if tts_tasks:
            await asyncio.gather(*tts_tasks, return_exceptions=True)
            for audio_seg in await _drain_tts_queue(tts_queue):
                yield {"event": "audio", "data": audio_seg.model_dump_json()}

        session_store.update(session)
        yield _sse_status("complete")

    except Exception as e:
        logger.error("[adk-orch] Follow-up error: %s", e, exc_info=True)
        yield {"event": "error", "data": json.dumps(translate_error_for_sse(e))}


# ---------------------------------------------------------------------------
# Critic Agent — Narrative Quality Review (Self-Correction)
# ---------------------------------------------------------------------------

async def run_critic_review(
    session: Session,
    arc_json: str | None = None,
) -> dict:
    """Run the critic agent to review a generated narrative.

    This enables self-correction by having a separate agent evaluate
    the narrative for quality, cultural authenticity, and coherence.

    Args:
        session: The session containing the generated narrative segments.
        arc_json: The narrative arc JSON (optional, will use session.arc_outline if not provided).

    Returns:
        A dict with review results including:
        - quality_review: Output from review_narrative_quality
        - authenticity_review: Output from review_cultural_authenticity
        - improvements: Output from suggest_narrative_improvements
        - overall_passed: Whether the narrative passed review
    """
    ui = session.user_input

    # Prepare narrative segments as JSON
    segments_json = json.dumps([
        {
            "type": seg.type,
            "content": seg.content,
            "trust_level": seg.trust_level,
            "act": seg.act,
            "sequence": seg.sequence,
        }
        for seg in session.segments
    ])

    # Use provided arc or session's arc
    arc = arc_json or json.dumps(session.arc_outline or {})

    # Combine all text for authenticity review
    narrative_text = "\n\n".join(
        seg.content for seg in session.segments
        if seg.type == "text" and seg.content
    )

    logger.info("[critic] Starting narrative review for session %s", session.session_id)

    try:
        # Run the three review tools directly (faster than full agent loop)
        quality_result = await review_narrative_quality(
            narrative_segments_json=segments_json,
            arc_json=arc,
            region=ui.region_of_origin,
            time_period=ui.time_period,
            family_name=ui.family_name,
        )

        authenticity_result = await review_cultural_authenticity(
            narrative_text=narrative_text,
            region=ui.region_of_origin,
            time_period=ui.time_period,
        )

        improvements_result = await suggest_narrative_improvements(
            quality_review_json=quality_result,
            authenticity_review_json=authenticity_result,
            arc_json=arc,
        )

        # Parse results
        quality = json.loads(quality_result)
        authenticity = json.loads(authenticity_result)
        improvements = json.loads(improvements_result)

        overall_passed = improvements.get("action") in ["approve", "approve_with_notes"]

        logger.info(
            "[critic] Review complete: quality=%.1f, authenticity=%s, action=%s",
            quality.get("quality_score", 0),
            authenticity.get("authenticity_score", 0),
            improvements.get("action"),
        )

        return {
            "quality_review": quality,
            "authenticity_review": authenticity,
            "improvements": improvements,
            "overall_passed": overall_passed,
            "overall_score": improvements.get("overall_quality", 5),
        }

    except Exception as e:
        logger.error("[critic] Review failed: %s", e, exc_info=True)
        return {
            "quality_review": {"error": str(e)},
            "authenticity_review": {"error": str(e)},
            "improvements": {"action": "error", "error": str(e)},
            "overall_passed": False,
            "overall_score": 0,
        }


async def run_adk_narrative_with_review(
    session: Session,
    audio: bool = False,
    max_revisions: int = 1,
) -> AsyncGenerator[dict, None]:
    """Run narrative generation with automatic critic review and self-correction.

    This is the enhanced version of run_adk_narrative that:
    1. Generates the initial narrative
    2. Runs the critic agent to review it
    3. If review fails with fixable issues, regenerates specific acts
    4. Yields the final approved narrative

    Args:
        session: The session to generate narrative for.
        audio: Whether to generate TTS audio.
        max_revisions: Maximum number of revision attempts (default 1).

    Yields:
        SSE events for the narrative generation and review process.
    """
    revision_count = 0

    while revision_count <= max_revisions:
        # Generate narrative (or regenerate on revision)
        if revision_count == 0:
            yield _sse_status("generating")
        else:
            yield _sse_status("revising", message=f"Revising narrative (attempt {revision_count})...")

        # Run the main narrative generation
        async for event in run_adk_narrative(session, audio=audio):
            # Don't emit "complete" yet if we need to review
            if event.get("event") == "status":
                status_data = json.loads(event.get("data", "{}"))
                if status_data.get("status") == "complete":
                    continue  # Skip, we'll emit after review
            yield event

        # Run critic review
        yield _sse_status("reviewing", message="Quality review in progress...")

        arc_json = json.dumps(session.arc_outline) if session.arc_outline else None
        review = await run_critic_review(session, arc_json)

        # Emit review results
        yield {
            "event": "review",
            "data": json.dumps({
                "passed": review["overall_passed"],
                "score": review["overall_score"],
                "action": review["improvements"].get("action"),
                "issues_count": len(review["improvements"].get("priority_fixes", [])),
            })
        }

        if review["overall_passed"]:
            logger.info("[critic] Narrative approved on attempt %d", revision_count + 1)
            yield _sse_status("complete", reviewed=True, score=review["overall_score"])
            return

        # Check if we should retry
        action = review["improvements"].get("action", "regenerate")
        if action == "regenerate" and revision_count < max_revisions:
            logger.info("[critic] Regeneration requested, clearing segments for retry")
            # Clear segments for regeneration
            session.segments = []
            session.arc_outline = None
            revision_count += 1
            continue
        else:
            # Accept with notes or max revisions reached
            logger.info("[critic] Accepting narrative with notes (action=%s, revisions=%d)",
                       action, revision_count)
            yield _sse_status(
                "complete",
                reviewed=True,
                score=review["overall_score"],
                notes=review["improvements"].get("priority_fixes", [])[:3]
            )
            return

    # Should not reach here, but just in case
    yield _sse_status("complete", reviewed=False)
