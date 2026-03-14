"""
Sankofa ADK Agent — Wraps the narrative pipeline as a Google Agent Development Kit agent.

This module defines Sankofa as an LlmAgent with tool functions for:
- Looking up cultural/historical context from the knowledge base
- Planning a 3-act narrative arc (with Google Search grounding)
- Generating interleaved text + image narrative segments
- Generating TTS audio narration

The agent can be used standalone via `adk run` or integrated into the
FastAPI backend for structured agent orchestration.
"""

import json
import logging
import uuid

from google.adk import Agent

from app.config import settings
from app.knowledge.loader import build_grounding_context
from app.models.schemas import UserInput
from app.services.gemini_service import generate_interleaved, generate_text
from app.services.trust_classifier import apply_trust_tags
from app.services.tts_service import generate_narration
from app.store import session_store

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool Functions — these are the capabilities the agent can invoke
# ---------------------------------------------------------------------------

media_store: dict[str, str] = {}

def lookup_cultural_context(
    region: str,
    time_period: str,
    family_name: str = "",
) -> str:
    """Look up cultural and historical context for a given region and time period.

    Use this tool when you need factual grounding about a specific region's
    history, culture, daily life, or diaspora patterns. Returns a text block
    of curated knowledge base entries.

    Args:
        region: The geographic region (e.g., "Ghana", "Jamaica", "Punjab").
        time_period: The historical era (e.g., "1700s", "pre-colonial", "1920s").
        family_name: Optional family name to personalize the context.

    Returns:
        A text summary of cultural and historical facts for the given region and era.
    """
    user_input = UserInput(
        family_name=family_name or "Unknown",
        region_of_origin=region,
        time_period=time_period,
    )
    context = build_grounding_context(user_input)
    # Determine basic coverage metadata based on whether fallback was used
    is_fallback = "not in our detailed knowledge base" in context.lower()

    metadata = {
        "region_match_confidence": "low" if is_fallback else "high",
        "decade_coverage_range": time_period,
        "gaps": ["No detailed regional data in knowledge base"] if is_fallback else ["May lack specific family history"],
        "content_length": len(context),
        "context_data": context
    }

    logger.info("[adk] lookup_cultural_context: %d chars for %s / %s", len(context), region, time_period)
    return json.dumps(metadata, indent=2)


def assess_context_quality(context_metadata_json: str) -> str:
    """Evaluate the quality and coverage of the culturally gathered context.

    Call this immediately after lookup_cultural_context to determine if the
    knowledge base coverage is sufficient.

    Args:
        context_metadata_json: The JSON string returned by lookup_cultural_context.

    Returns:
        A string indicating 'rich', 'moderate', or 'sparse'. If 'sparse', you should
        call research_region_history before planning the narrative.
    """
    try:
        data = json.loads(context_metadata_json)
        if data.get("region_match_confidence") == "low":
            return "sparse"
        return "rich"
    except Exception:
        return "moderate"


async def research_region_history(region: str, time_period: str) -> str:
    """Use Google Search grounding to gather historical context for uncovered regions.

    Call this ONLY if assess_context_quality returns 'sparse' or 'none'.

    Args:
        region: The geographic region.
        time_period: The historical era.

    Returns:
        A rich historical context string retrieved via web search.
    """
    prompt = f"Provide a detailed historical and cultural overview of {region} during {time_period}. Focus on daily life, major events, social structure, and historical context. This will be used to ground a family heritage story."
    result = await generate_text(prompt, grounded=True)
    logger.info("[adk] research_region_history: gathered %d chars via search", len(result))
    return result


async def plan_narrative_arc(
    region: str,
    time_period: str,
    family_name: str,
    cultural_context: str,
    feedback: str = "",
) -> str:
    """Plan a 3-act narrative arc for a heritage story using Gemini.

    Call this after context is gathered to structure the narrative.
    Returns a JSON string with act1_setting, act2_people, act3_thread,
    tone, and narrative_voice.

    If this fails, it recovers gracefully using a template.

    Args:
        region: The geographic region of origin.
        time_period: The historical era for the story.
        family_name: The family name being narrated.
        cultural_context: Cultural/historical context.
        feedback: Optional previous validation feedback to address.

    Returns:
        A JSON string containing the 3-act narrative arc structure.
    """
    prompt = f"""You are a narrative architect planning an ancestral heritage story.

Given the following cultural and historical context about {region}
during {time_period}, plan a three-act narrative structure for the
{family_name} family heritage story.

=== GROUNDING CONTEXT ===
{cultural_context[:2000]}\n"""

    if feedback:
        prompt += f"""\n=== FEEDBACK TO ADDRESS ===
The previous plan failed validation for these reasons:
{feedback}
Please revise the arc to specifically address these issues.\n"""

    prompt += """\n=== TASK ===
Output a JSON object with this structure:
{
  "act1_setting": {
    "title": "A short evocative title",
    "focus": "What aspect of landscape/environment to describe",
    "key_facts": ["2-3 historical facts to weave in"]
  },
  "act2_people": {
    "title": "A short evocative title",
    "focus": "What aspect of daily life/culture to center",
    "key_facts": ["2-3 cultural/historical facts"]
  },
  "act3_thread": {
    "title": "A short evocative title",
    "focus": "What thread connects past to present",
    "key_facts": ["2-3 facts about diaspora/cultural survival"]
  },
  "tone": "The specific emotional register",
  "narrative_voice": "How the griot narrator should speak"
}

Output ONLY the JSON, no other text."""

    try:
        response = await generate_text(prompt, grounded=True)
        logger.info("[adk] plan_narrative_arc: received %d chars", len(response))
        return response
    except Exception as e:
        logger.warning(f"[adk] plan_narrative_arc failed: {e}. Falling back to template.")
        await notify_user("I had trouble planning the story structure, so I will use a reliable traditional format.")
        fallback = {
            "act1_setting": {"title": "The Land", "focus": "landscape", "key_facts": []},
            "act2_people": {"title": "The People", "focus": "daily life", "key_facts": []},
            "act3_thread": {"title": "Connection", "focus": "diaspora", "key_facts": []},
            "tone": "warm and reverent",
            "narrative_voice": "West African griot"
        }
        return json.dumps(fallback)


async def validate_narrative_arc(arc_json: str, cultural_context: str) -> str:
    """Validate a planned narrative arc against the gathered cultural context.

    Call this after plan_narrative_arc to ensure the story is specific, grounded,
    and has a strong emotional progression.

    Args:
        arc_json: The JSON string output from plan_narrative_arc.
        cultural_context: The historical and cultural context string.

    Returns:
        A validation report string. If it says 'PASS', you can proceed.
        If it says 'FAIL' with reasons, you must call plan_narrative_arc again
        with a modified prompt to address the feedback.
    """
    prompt = f"""You are a master storyteller evaluating an ancestral narrative arc.
Review the proposed arc against the provided historical context.

=== HISTORICAL CONTEXT ===
{cultural_context[:3000]}

=== NARRATIVE ARC ===
{arc_json[:2000]}

Evaluate based on:
1. Specificity: Does it use real historical facts/names/practices, or is it generic?
2. Coverage: Does each act draw on different aspects of the context?
3. Emotional progression: Does it build toward a strong past-to-present connection?
4. Trust tags: Are the claims plausibly grounded in the context?

If the arc is strong and grounded, respond only with "PASS".
If it is weak, generic, or ungrounded, respond with "FAIL:" followed by specific feedback on what to fix."""

    result = await generate_text(prompt)
    logger.info("[adk] validate_narrative_arc: result=%s", result[:50].replace('\n', ' '))
    return result


async def generate_act_segments(
    act_number: int,
    region: str,
    time_period: str,
    family_name: str,
    cultural_context: str,
    arc_json: str,
    previous_narrative: str = "",
    image_density: str = "medium",
) -> str:
    """Generate interleaved text + image narrative for a SPECIFIC act (1, 2, or 3).

    Call this three times (once per act) sequentially to build the full narrative.
    Between acts, you can adjust the prompt or image density based on previous outputs.

    Args:
        act_number: The act to generate (1, 2, or 3).
        region: The geographic region.
        time_period: The historical era.
        family_name: The family name.
        cultural_context: Cultural context string.
        arc_json: The arc plan JSON.
        previous_narrative: The text of previously generated acts (to maintain continuity).
        image_density: 'high' (multiple images), 'medium' (one image), or 'none' (text only).

    Returns:
        A JSON string containing an array of narrative segments for this act.
    """
    density_instruction = "interleaved with 1 watercolor-style image."
    if image_density == "high":
        density_instruction = "interleaved with 2-3 watercolor-style images."
    elif image_density == "none":
        density_instruction = "using ONLY text, with NO images."

    prompt = f"""You are Sankofa, an ancestral heritage narrator in the tradition of a
West African griot. Generate a rich, immersive narrative for ACT {act_number} of the
{family_name} family heritage story from {region} during {time_period}.

=== CULTURAL/HISTORICAL GROUNDING ===
{cultural_context[:4000]}

=== NARRATIVE ARC ===
{arc_json[:2000]}
"""

    if previous_narrative:
        prompt += f"""\n=== PREVIOUS ACTS (For Continuity) ===
Follow seamlessly from this existing narrative:
{previous_narrative[-3000:]}\n"""

    prompt += """
=== TASK ===
Generate 3–4 paragraphs of narrative text for ACT {act_number}, {density_instruction}
Use warm earth tones, gold accents, and period-appropriate details for any images.
Tag each paragraph with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED].
Use the warm, unhurried cadence of a West African griot."""

    try:
        segments = await generate_interleaved(prompt)
    except Exception as e:
        logger.warning(f"[adk] generate_act_segments failed ({e}). Retrying with text-only...")
        await notify_user(f"Encountered an issue generating Act {act_number} (possible content filter). Switching to text-only narration.")

        # Fallback to text only
        prompt_text_only = prompt.replace(density_instruction, "using ONLY text, with NO images.")
        try:
            segments = await generate_interleaved(prompt_text_only)
        except Exception as retry_e:
            logger.error(f"[adk] Text-only retry also failed: {retry_e}")
            segments = []

    if segments:
        segments = apply_trust_tags(segments)

    # Assign act number and mark first image as hero for act 1
    result = []
    for i, seg in enumerate(segments):
        seg.act = act_number
        if act_number == 1 and seg.type == "image" and i == 0:
            seg.is_hero = True

        dump = seg.model_dump()
        if dump.get("media_data"):
            media_ref = str(uuid.uuid4())
            media_store[media_ref] = dump["media_data"]
            dump["media_data"] = None  # Remove from LLM context!
            dump["media_reference"] = media_ref
        result.append(dump)

    logger.info("[adk] generate_act_segments: produced %d segments for act %d", len(result), act_number)
    return json.dumps(result)


async def enrich_segment(segment_text: str, context_query: str) -> str:
    """Run a targeted search to enrich a Reconstructed segment with real history.

    Call this between acts if a generated segment is tagged [RECONSTRUCTED] but you
    suspect real historical details could be found to upgrade it to [HISTORICAL].

    Args:
        segment_text: The generated text that needs more factual grounding.
        context_query: A specific search query (e.g. "Trade routes in Ghana 1700s").

    Returns:
        A grounded, factually enriched version of the segment.
    """
    prompt = f"""Rewrite and enrich the following narrative segment using specific
historical facts from a grounded search. Keep the warm, griot-style tone.
Tag it with [HISTORICAL] if you find solid facts, or [CULTURAL] if you find general practices.

Original Segment:
{segment_text}

=== TASK ===
Search for: {context_query}
Then return the enriched segment."""

    result = await generate_text(prompt, grounded=True)
    logger.info("[adk] enrich_segment: enriched segment using query '%s'", context_query)
    return result


async def generate_audio_narration(text: str) -> str:
    """Generate TTS audio narration for a text passage using Gemini TTS.

    Call this for each text segment to create audio narration in the
    warm, griot-inspired voice.

    Args:
        text: The text passage to narrate.

    Returns:
        A JSON string with base64 audio data and mime type, or an error message.
    """
    try:
        result = await generate_narration(text)
        if result:
            audio_data, mime_type = result
            return json.dumps({"audio_data": audio_data, "mime_type": mime_type})
    except Exception as e:
        logger.warning(f"[adk] TTS generation failed: {e}")
        await notify_user("Audio generation unavailable for this passage. Continuing with text.")

    return json.dumps({"error": "TTS generation failed"})


async def notify_user(message: str) -> str:
    """Send a status message to the user about generation progress or issues.

    Call this when encountering errors, adapting the plan, or switching modes
    (e.g. falling back to text-only due to sensitive content).

    Args:
        message: The status message to show to the user.

    Returns:
        Confirmation string.
    """
    # In a full deployment, this would push to an async queue connected to an SSE endpoint.
    logger.info(f"[adk SSE NOTIFY] {message}")
    return "Notification sent."


def recall_narrative_context(session_id: str) -> str:
    """Retrieve the previous narrative and its trust tags for follow-up explorations.

    Call this when a user asks a follow-up question to recall what was already generated.

    Args:
        session_id: The active session ID.

    Returns:
        A formatted string of all previous text segments and their trust levels.
    """
    session = session_store.get(session_id)
    if not session:
        return "No previous narrative found for this session."

    context_parts = []
    for seg in session.segments:
        if seg.type == "text" and seg.content:
            context_parts.append(f"[{seg.trust_level.upper()}] {seg.content}")

    return "\n".join(context_parts)


async def deep_dive(topic: str, cultural_context: str) -> str:
    """Generate a focused mini-narrative (1 act) exploring a specific aspect in depth.

    Call this when the user asks a follow-up question like 'tell me more about the trade routes.'

    Args:
        topic: The specific aspect to explore.
        cultural_context: The gathered historical context.

    Returns:
        A detailed, focused text/image segment explaining the topic.
    """
    prompt = f"""You are Sankofa, a West African griot. Deep dive into this specific topic: '{topic}'.

=== HISTORICAL CONTEXT ===
{cultural_context[:3000]}

Write 1-2 rich paragraphs explaining this topic in detail within the context of the region.
Prepend paragraphs with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED]."""

    segments = await generate_interleaved(prompt)
    segments = apply_trust_tags(segments)

    result = []
    for seg in segments:
        dump = seg.model_dump()
        if dump.get("media_data"):
            media_ref = str(uuid.uuid4())
            media_store[media_ref] = dump["media_data"]
            dump["media_data"] = None  # Remove from LLM context!
            dump["media_reference"] = media_ref
        result.append(dump)

    logger.info("[adk] deep_dive: produced %d segments", len(result))
    return json.dumps(result)


# ---------------------------------------------------------------------------
# ADK Agent Definition
# ---------------------------------------------------------------------------

sankofa_agent_description = (
    "Sankofa is an AI griot that transforms personal and familial inputs into "
    "immersive, multimodal ancestral heritage narratives. It combines historical "
    "research, cultural knowledge, and oral storytelling traditions to weave "
    "together text, images, and audio narration."
)

sankofa_agent_instruction = """You are Sankofa, an ancestral heritage narrator in the tradition of a
West African griot. Your purpose is to help users discover and connect with their
ancestral heritage through immersive storytelling.

When a user provides their family name, region of origin, and time period, follow this process:

1. Gather Context: Use `lookup_cultural_context` to query the knowledge base.
2. Evaluate Context: Use `assess_context_quality` on the result.
   - If it returns "sparse" or "none", use `research_region_history` to gather better grounding.
3. Plan: Use `plan_narrative_arc` to structure a 3-act story.
4. Validate: Use `validate_narrative_arc` to review the plan. If it FAILS, call `plan_narrative_arc` again providing the feedback string (do this at most once).
5. Generate Act 1: Use `generate_act_segments` for Act 1. You specify `image_density`.
6. Review & Enrich: Review Act 1. If it needs better grounding, use `enrich_segment`.
7. Generate Act 2: Use `generate_act_segments` for Act 2, passing Act 1's text as `previous_narrative`.
8. Generate Act 3: Use `generate_act_segments` for Act 3, passing previous acts text.
9. Audio (Optional): Use `generate_audio_narration` for text segments.
10. Notifications: Use `notify_user` to communicate if you must drop images or audio.

FOLLOW-UP EXPLORATION:
If the user asks a follow-up question:
1. Use `recall_narrative_context` with their session_id to read the existing story.
2. If the question requires a short narrative exploration, use `deep_dive` to generate a 1-act vignette.
3. Suggest proactively: Analyze the recalled context, and if parts were [RECONSTRUCTED],
   you can ask the user if they have any family oral traditions to fill the gaps.

Always maintain a warm, reverent tone. Clearly distinguish between historical facts,
cultural practices, and imaginative reconstruction. Never fabricate specific genealogical
claims — instead, paint a vivid picture of the world their ancestors inhabited.

The three acts should flow naturally:
- Act 1 (Setting): The land, landscape, and atmosphere of the ancestral region
- Act 2 (People): Daily life, cultural practices, and community
- Act 3 (Thread): The connection between past and present, diaspora and survival

IMPORTANT: Always return the raw data from tool calls. Do NOT summarize or paraphrase
the output of generate_act_segments or deep_dive — the orchestrator needs the full
JSON segment arrays to stream them to the user. If the user message says to skip
generate_audio_narration, respect that instruction."""

sankofa_agent_tools = [
    lookup_cultural_context,
    assess_context_quality,
    research_region_history,
    plan_narrative_arc,
    validate_narrative_arc,
    generate_act_segments,
    enrich_segment,
    generate_audio_narration,
    recall_narrative_context,
    deep_dive,
    notify_user,
]

sankofa_agent = Agent(
    model=settings.GEMINI_PLANNING_MODEL,
    name="sankofa_heritage_narrator",
    description=sankofa_agent_description,
    instruction=sankofa_agent_instruction,
    tools=sankofa_agent_tools,
)

sankofa_live_agent = Agent(
    model=settings.GEMINI_LIVE_MODEL,
    name="sankofa_heritage_live_narrator",
    description=sankofa_agent_description,
    instruction=sankofa_agent_instruction,
    tools=sankofa_agent_tools,
)
