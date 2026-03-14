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
from app.services.adk_agent import media_store, sankofa_agent
from app.services.tts_service import generate_narration
from app.store import session_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK Runner setup (separate from the app's session store)
# ---------------------------------------------------------------------------

_adk_session_service = InMemorySessionService()
_runner = Runner(
    agent=sankofa_agent,
    app_name="sankofa",
    session_service=_adk_session_service,
)

# ---------------------------------------------------------------------------
# "Thinking aloud" messages — shown to the user as the agent works
# ---------------------------------------------------------------------------

_THINKING_MESSAGES = {
    "lookup_cultural_context": "Consulting the knowledge base on {region} heritage...",
    "assess_context_quality": "Evaluating available historical records...",
    "research_region_history": "Searching for additional context on {region} during {time_period}...",
    "plan_narrative_arc": "Planning a three-act arc for the {family_name} family story...",
    "validate_narrative_arc": "Reviewing the story structure for historical accuracy...",
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
      -> plan_narrative_arc -> validate_narrative_arc -> generate_act_segments x3

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
                                    async def _do_tts(s=seg, q=tts_queue):
                                        try:
                                            result = await generate_narration(s.content)
                                            if result:
                                                audio_data, mime = result
                                                await q.put(NarrativeSegment(
                                                    type="audio",
                                                    content=(s.content[:100] if s.content else ""),
                                                    media_data=audio_data,
                                                    media_type=mime,
                                                    trust_level=s.trust_level,
                                                    sequence=s.sequence,
                                                    act=s.act,
                                                ))
                                        except Exception as e:
                                            logger.warning("[adk-orch] TTS failed: %s", e)

                                    tts_tasks.append(asyncio.create_task(_do_tts()))

                                # Stagger delivery for natural feel
                                delay = 1.2 if seg.type == "image" else (0.6 if i == 0 else 0.35)
                                await asyncio.sleep(delay)
                        else:
                            logger.warning(
                                "[adk-orch] Could not parse segments from generate_act_segments"
                            )

        # --- Collect TTS results ---
        if tts_tasks:
            yield _sse_status("generating_audio")
            await asyncio.gather(*tts_tasks, return_exceptions=True)
            while not tts_queue.empty():
                audio_seg = await tts_queue.get()
                yield {"event": "audio", "data": audio_seg.model_dump_json()}

        # Persist session
        session_store.update(session)

        yield _sse_status("complete")

    except Exception as e:
        logger.error("[adk-orch] Narrative generation error: %s", e, exc_info=True)
        yield {"event": "error", "data": json.dumps({"error": str(e)})}


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
                                    async def _do_tts(s=seg, q=tts_queue):
                                        try:
                                            result = await generate_narration(s.content)
                                            if result:
                                                audio_data, mime = result
                                                await q.put(NarrativeSegment(
                                                    type="audio",
                                                    content=s.content[:100],
                                                    media_data=audio_data,
                                                    media_type=mime,
                                                    trust_level=s.trust_level,
                                                    sequence=s.sequence,
                                                    act=s.act,
                                                ))
                                        except Exception as e:
                                            logger.warning("[adk-orch] TTS followup failed: %s", e)

                                    tts_tasks.append(asyncio.create_task(_do_tts()))

                                await asyncio.sleep(0.35)

        if tts_tasks:
            yield _sse_status("generating_audio")
            await asyncio.gather(*tts_tasks, return_exceptions=True)
            while not tts_queue.empty():
                audio_seg = await tts_queue.get()
                yield {"event": "audio", "data": audio_seg.model_dump_json()}

        session_store.update(session)
        yield _sse_status("complete")

    except Exception as e:
        logger.error("[adk-orch] Follow-up error: %s", e, exc_info=True)
        yield {"event": "error", "data": json.dumps({"error": str(e)})}
