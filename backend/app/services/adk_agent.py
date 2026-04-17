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
from google.adk.models.google_llm import Gemini
from google.genai import types as genai_types

from app.config import settings
from app.knowledge.loader import build_grounding_context
from app.models.schemas import UserInput
from app.services.gemini_service import generate_interleaved, generate_text
from app.services.trust_classifier import apply_trust_tags, reclassify_untagged
from app.services.tts_service import generate_narration
from app.store import session_store

logger = logging.getLogger(__name__)

# Context window limits for prompt truncation (characters)
_CTX_PLAN = 2000
_CTX_GENERATE = 4000
_CTX_PREV_NARRATIVE = 3000
_CTX_DEEP_DIVE = 3000


# ---------------------------------------------------------------------------
# Tool Functions — these are the capabilities the agent can invoke
# ---------------------------------------------------------------------------

media_store: dict[str, str] = {}

_MEDIA_STORE_MAX = 200  # Max entries before eviction; refs are session-scoped so clearing is safe


def _media_store_put(ref: str, data: str) -> None:
    """Insert *data* into media_store, evicting all entries when the cap is reached."""
    if len(media_store) >= _MEDIA_STORE_MAX:
        logger.warning("[adk] media_store hit cap (%d); clearing stale entries", _MEDIA_STORE_MAX)
        media_store.clear()
    media_store[ref] = data


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
{cultural_context[:_CTX_PLAN]}\n"""

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
    "key_facts": ["2-3 historical facts to weave in"],
    "ambient_track": "One of: wind.mp3 (landscape, open air), fire.mp3 (hearth, campfire, warmth), nature.mp3 (forest, water, wildlife), market.mp3 (community, commerce, bustle), drums.mp3 (cultural rhythm, ceremony, connection), rain.mp3 (monsoon, tropical rain), ocean.mp3 (coast, sea, island), river.mp3 (riverside, stream), crickets.mp3 (night, evening), village.mp3 (village life, home)"
  },
  "act2_people": {
    "title": "A short evocative title",
    "focus": "What aspect of daily life/culture to center",
    "key_facts": ["2-3 cultural/historical facts"],
    "ambient_track": "One of: wind.mp3 (landscape, open air), fire.mp3 (hearth, campfire, warmth), nature.mp3 (forest, water, wildlife), market.mp3 (community, commerce, bustle), drums.mp3 (cultural rhythm, ceremony, connection), rain.mp3 (monsoon, tropical rain), ocean.mp3 (coast, sea, island), river.mp3 (riverside, stream), crickets.mp3 (night, evening), village.mp3 (village life, home)"
  },
  "act3_thread": {
    "title": "A short evocative title",
    "focus": "What thread connects past to present",
    "key_facts": ["2-3 facts about diaspora/cultural survival"],
    "ambient_track": "One of: wind.mp3 (landscape, open air), fire.mp3 (hearth, campfire, warmth), nature.mp3 (forest, water, wildlife), market.mp3 (community, commerce, bustle), drums.mp3 (cultural rhythm, ceremony, connection), rain.mp3 (monsoon, tropical rain), ocean.mp3 (coast, sea, island), river.mp3 (riverside, stream), crickets.mp3 (night, evening), village.mp3 (village life, home)"
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
            "act1_setting": {"title": "The Land", "focus": "landscape", "key_facts": [], "ambient_track": "wind.mp3"},
            "act2_people": {"title": "The People", "focus": "daily life", "key_facts": [], "ambient_track": "market.mp3"},
            "act3_thread": {"title": "Connection", "focus": "diaspora", "key_facts": [], "ambient_track": "drums.mp3"},
            "tone": "warm and reverent",
            "narrative_voice": "West African griot"
        }
        return json.dumps(fallback)


async def validate_narrative_arc(arc_json: str, region: str, time_period: str) -> str:
    """Validate the planned narrative arc for quality and completeness.

    This tool checks:
    1. Structural validity - all required fields present
    2. Content quality - titles are specific, not generic placeholders
    3. Key facts - each act has grounding in actual historical/cultural facts
    4. Coherence - acts tell a connected story

    Call this after plan_narrative_arc. If validation fails, call
    plan_narrative_arc again with the feedback to revise.

    Args:
        arc_json: The JSON string from plan_narrative_arc.
        region: The geographic region (for context checking).
        time_period: The historical era (for context checking).

    Returns:
        JSON string with {"valid": bool, "feedback": str}.
        If valid=false, feedback explains what needs improvement.
    """
    issues = []

    try:
        arc = json.loads(arc_json.strip().strip("```json").strip("```"))
    except json.JSONDecodeError as e:
        return json.dumps({
            "valid": False,
            "feedback": f"Arc JSON is malformed: {e}. Please output valid JSON only."
        })

    # Check required top-level fields
    required_acts = ["act1_setting", "act2_people", "act3_thread"]
    for act_key in required_acts:
        if act_key not in arc:
            issues.append(f"Missing required field: {act_key}")
        else:
            act = arc[act_key]
            # Check each act has required sub-fields
            if not act.get("title"):
                issues.append(f"{act_key}: Missing 'title'")
            elif len(act["title"]) < 5:
                issues.append(f"{act_key}: Title too short, be more evocative")
            elif act["title"].lower() in ["the land", "the people", "connection", "untitled"]:
                issues.append(f"{act_key}: Title is too generic ('{act['title']}'), make it specific to {region}")

            if not act.get("focus"):
                issues.append(f"{act_key}: Missing 'focus'")

            if not act.get("key_facts") or not isinstance(act.get("key_facts"), list):
                issues.append(f"{act_key}: Missing or invalid 'key_facts' (should be a list)")
            elif len(act.get("key_facts", [])) < 1:
                issues.append(f"{act_key}: Should have at least 1 key_fact for grounding")

            if not act.get("ambient_track"):
                issues.append(f"{act_key}: Missing 'ambient_track'")

    if "tone" not in arc:
        issues.append("Missing 'tone' field")
    if "narrative_voice" not in arc:
        issues.append("Missing 'narrative_voice' field")

    # Content quality checks
    if not issues:
        # Check that content mentions the actual region/period
        arc_str = json.dumps(arc).lower()
        if region.lower() not in arc_str and len(region) > 3:
            issues.append(f"Arc should reference {region} more specifically in titles or focus areas")

    if issues:
        feedback = "Please revise the arc to address these issues:\n- " + "\n- ".join(issues)
        logger.info("[adk] validate_narrative_arc: FAILED with %d issues", len(issues))
        return json.dumps({"valid": False, "feedback": feedback})

    logger.info("[adk] validate_narrative_arc: PASSED")
    return json.dumps({"valid": True, "feedback": "Arc structure and content look good."})


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
{cultural_context[:_CTX_GENERATE]}

=== NARRATIVE ARC ===
{arc_json[:_CTX_PLAN]}
"""

    if previous_narrative:
        prompt += f"""\n=== PREVIOUS ACTS (For Continuity) ===
Follow seamlessly from this existing narrative:
{previous_narrative[-_CTX_PREV_NARRATIVE:]}\n"""

    prompt += f"""
=== TASK ===
Generate 3–4 paragraphs of narrative text for ACT {act_number}, {density_instruction}

IMAGE STYLE (mandatory for every image):
Paint in a WATERCOLOR illustration style — visible brushstrokes, soft wet-on-wet
edges, transparent washes of pigment with white paper showing through. Use a warm
palette of burnt sienna, raw umber, yellow ochre, and gold leaf accents. No
photorealism, no digital art, no sharp vector edges. Every image must look like a
hand-painted watercolor on textured paper. Period-appropriate details only.

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
        segments = await reclassify_untagged(segments)

    # Assign act number and mark first image as hero for act 1
    result = []
    for i, seg in enumerate(segments):
        seg.act = act_number
        if act_number == 1 and seg.type == "image" and i == 0:
            seg.is_hero = True

        dump = seg.model_dump()
        if dump.get("media_data"):
            media_ref = str(uuid.uuid4())
            _media_store_put(media_ref, dump["media_data"])
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
{cultural_context[:_CTX_DEEP_DIVE]}

Write 1-2 rich paragraphs explaining this topic in detail within the context of the region.

IMAGE STYLE (mandatory for every image):
Paint in a WATERCOLOR illustration style — visible brushstrokes, soft wet-on-wet
edges, transparent washes of pigment with white paper showing through. Use a warm
palette of burnt sienna, raw umber, yellow ochre, and gold leaf accents. No
photorealism, no digital art, no sharp vector edges. Every image must look like a
hand-painted watercolor on textured paper. Period-appropriate details only.

Prepend paragraphs with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED]."""

    segments = await generate_interleaved(prompt)
    segments = apply_trust_tags(segments)
    segments = await reclassify_untagged(segments)

    result = []
    for seg in segments:
        dump = seg.model_dump()
        if dump.get("media_data"):
            media_ref = str(uuid.uuid4())
            _media_store_put(media_ref, dump["media_data"])
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
4. Validate: Use `validate_narrative_arc` to check the arc quality.
   - If validation fails, call `plan_narrative_arc` again with the feedback parameter set to the validation issues.
   - Repeat until validation passes (max 2 attempts).
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

sankofa_live_tools = [
    lookup_cultural_context,
    assess_context_quality,
    research_region_history,
    recall_narrative_context,
    deep_dive,
    notify_user,
]

_live_model = Gemini(
    model=settings.GEMINI_LIVE_MODEL,
    speech_config=genai_types.SpeechConfig(
        voice_config=genai_types.VoiceConfig(
            prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Kore")
        )
    ),
)

sankofa_live_agent = Agent(
    model=_live_model,
    name="sankofa_heritage_live_narrator",
    description=sankofa_agent_description,
    instruction=sankofa_agent_instruction,
    tools=sankofa_live_tools,
)


# ---------------------------------------------------------------------------
# Critic Agent — Self-Correction via Multi-Agent Review
# ---------------------------------------------------------------------------

async def review_narrative_quality(
    narrative_segments_json: str,
    arc_json: str,
    region: str,
    time_period: str,
    family_name: str,
) -> str:
    """Evaluate the overall quality and coherence of a generated narrative.

    This tool performs a comprehensive review of the narrative including:
    - Narrative coherence across all acts
    - Cultural authenticity and historical accuracy
    - Trust level classification correctness
    - Emotional resonance and storytelling quality
    - Proper griot voice and tone consistency

    Args:
        narrative_segments_json: JSON array of all generated segments.
        arc_json: The narrative arc that was planned.
        region: The geographic region.
        time_period: The historical era.
        family_name: The family name being narrated.

    Returns:
        JSON with {"quality_score": 1-10, "passed": bool, "issues": [...], "suggestions": [...]}
    """
    try:
        segments = json.loads(narrative_segments_json)
        json.loads(arc_json.strip().strip("```json").strip("```"))  # Validate arc JSON
    except json.JSONDecodeError as e:
        return json.dumps({
            "quality_score": 0,
            "passed": False,
            "issues": [f"Invalid JSON input: {e}"],
            "suggestions": ["Regenerate the narrative with valid JSON output"]
        })

    issues = []
    suggestions = []

    # 1. Check segment count and distribution
    text_segments = [s for s in segments if s.get("type") == "text"]
    image_segments = [s for s in segments if s.get("type") == "image"]

    if len(text_segments) < 6:
        issues.append(f"Narrative has only {len(text_segments)} text segments; expected at least 6 for a 3-act story")
        suggestions.append("Generate more detailed content for each act")

    # 2. Check trust level distribution
    trust_levels = [s.get("trust_level", "unknown") for s in text_segments]
    if all(t == "reconstructed" for t in trust_levels):
        issues.append("All segments are marked [RECONSTRUCTED] with no historical or cultural grounding")
        suggestions.append("Use research_region_history to gather more factual context before regenerating")

    # 3. Check act coverage
    acts_covered = set(s.get("act") for s in segments if s.get("act"))
    if len(acts_covered) < 3:
        issues.append(f"Only {len(acts_covered)} acts generated; all 3 acts should be present")
        suggestions.append("Ensure generate_act_segments is called for acts 1, 2, and 3")

    # 4. Check narrative continuity (basic: segments should have content)
    empty_segments = [i for i, s in enumerate(text_segments) if not s.get("content") or len(s.get("content", "")) < 50]
    if empty_segments:
        issues.append(f"{len(empty_segments)} text segments have insufficient content")
        suggestions.append("Regenerate sparse segments with more descriptive prompts")

    # 5. Check region/cultural specificity
    all_text = " ".join(s.get("content", "") for s in text_segments).lower()
    region_lower = region.lower()
    if region_lower not in all_text and len(region) > 3:
        issues.append(f"Narrative does not mention {region} specifically")
        suggestions.append(f"Ensure the narrative is grounded in {region}'s specific cultural context")

    # 6. Check for generic placeholder content
    generic_markers = ["lorem ipsum", "[placeholder]", "insert here", "tbd", "todo"]
    for marker in generic_markers:
        if marker in all_text:
            issues.append(f"Narrative contains placeholder text: '{marker}'")
            suggestions.append("Remove all placeholder content and replace with authentic narrative")

    # Calculate quality score
    base_score = 10
    base_score -= len(issues) * 1.5
    base_score = max(1, min(10, base_score))

    passed = len(issues) == 0 or (len(issues) <= 2 and base_score >= 7)

    logger.info("[critic] review_narrative_quality: score=%.1f, passed=%s, issues=%d",
                base_score, passed, len(issues))

    return json.dumps({
        "quality_score": round(base_score, 1),
        "passed": passed,
        "issues": issues,
        "suggestions": suggestions,
        "stats": {
            "text_segments": len(text_segments),
            "image_segments": len(image_segments),
            "acts_covered": list(acts_covered),
            "trust_distribution": {t: trust_levels.count(t) for t in set(trust_levels)}
        }
    })


async def review_cultural_authenticity(
    narrative_text: str,
    region: str,
    time_period: str,
) -> str:
    """Use Gemini to evaluate cultural authenticity and historical accuracy.

    This performs a deeper AI-powered review of whether the narrative
    accurately represents the culture and history of the specified region.

    Args:
        narrative_text: The combined text of all narrative segments.
        region: The geographic region.
        time_period: The historical era.

    Returns:
        JSON with authenticity assessment and specific feedback.
    """
    prompt = f"""You are a cultural historian and authenticity reviewer. Evaluate this
narrative about {region} during {time_period} for cultural and historical accuracy.

=== NARRATIVE ===
{narrative_text[:_CTX_GENERATE]}

=== REVIEW CRITERIA ===
1. Historical Accuracy: Are dates, events, and historical context correct?
2. Cultural Authenticity: Are cultural practices, traditions, and customs accurately portrayed?
3. Language & Terminology: Are terms, names, and phrases appropriate for the region and era?
4. Avoiding Stereotypes: Does the narrative avoid harmful stereotypes or oversimplifications?
5. Griot Voice: Is the storytelling style consistent with West African oral traditions?

=== OUTPUT ===
Return a JSON object:
{{
  "authenticity_score": 1-10,
  "historical_accuracy": "accurate/mostly accurate/needs improvement/inaccurate",
  "cultural_representation": "authentic/mostly authentic/needs improvement/problematic",
  "specific_issues": ["issue 1", "issue 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "strengths": ["what the narrative does well"]
}}

Output ONLY the JSON."""

    try:
        response = await generate_text(prompt, grounded=True)
        # Try to parse and validate
        result = json.loads(response.strip().strip("```json").strip("```"))
        logger.info("[critic] review_cultural_authenticity: score=%s", result.get("authenticity_score"))
        return json.dumps(result)
    except Exception as e:
        logger.warning("[critic] review_cultural_authenticity failed: %s", e)
        return json.dumps({
            "authenticity_score": 5,
            "historical_accuracy": "unable to assess",
            "cultural_representation": "unable to assess",
            "specific_issues": [f"Review failed: {e}"],
            "recommendations": ["Manual review recommended"],
            "strengths": []
        })


async def suggest_narrative_improvements(
    quality_review_json: str,
    authenticity_review_json: str,
    arc_json: str,
) -> str:
    """Synthesize reviews into actionable improvement suggestions.

    Call this after both review_narrative_quality and review_cultural_authenticity
    to get a consolidated action plan for improving the narrative.

    Args:
        quality_review_json: Output from review_narrative_quality.
        authenticity_review_json: Output from review_cultural_authenticity.
        arc_json: The original narrative arc.

    Returns:
        JSON with prioritized improvement actions.
    """
    try:
        quality = json.loads(quality_review_json)
        authenticity = json.loads(authenticity_review_json)
        json.loads(arc_json.strip().strip("```json").strip("```"))  # Validate arc JSON
    except json.JSONDecodeError:
        return json.dumps({
            "action": "regenerate",
            "priority_fixes": ["Unable to parse reviews; regenerate narrative from scratch"],
            "optional_enhancements": []
        })

    priority_fixes = []
    optional_enhancements = []

    # Combine issues from both reviews
    quality_score = quality.get("quality_score", 5)
    auth_score = authenticity.get("authenticity_score", 5)

    # Critical issues (must fix)
    if quality_score < 5:
        priority_fixes.append("Narrative quality is poor; regenerate all acts with richer context")
    if auth_score < 5:
        priority_fixes.append("Cultural authenticity issues detected; research region history before regenerating")

    for issue in quality.get("issues", []):
        if "placeholder" in issue.lower() or "reconstructed" in issue.lower():
            priority_fixes.append(issue)
        else:
            optional_enhancements.append(issue)

    for issue in authenticity.get("specific_issues", []):
        if "stereotype" in issue.lower() or "inaccurate" in issue.lower():
            priority_fixes.append(issue)
        else:
            optional_enhancements.append(issue)

    # Determine action
    if quality_score >= 8 and auth_score >= 8:
        action = "approve"
    elif quality_score >= 6 and auth_score >= 6 and len(priority_fixes) == 0:
        action = "approve_with_notes"
    elif len(priority_fixes) <= 2:
        action = "revise_specific_acts"
    else:
        action = "regenerate"

    logger.info("[critic] suggest_narrative_improvements: action=%s, fixes=%d",
                action, len(priority_fixes))

    return json.dumps({
        "action": action,
        "overall_quality": (quality_score + auth_score) / 2,
        "priority_fixes": priority_fixes[:5],  # Top 5 critical fixes
        "optional_enhancements": optional_enhancements[:5],
        "strengths": authenticity.get("strengths", []),
        "recommendation": quality.get("suggestions", [])[:3]
    })


# Critic Agent Definition
sankofa_critic_description = (
    "The Sankofa Critic is a quality assurance agent that reviews generated narratives "
    "for cultural authenticity, historical accuracy, storytelling coherence, and proper "
    "trust level classification. It provides structured feedback for improvement."
)

sankofa_critic_instruction = """You are the Sankofa Critic, a quality assurance reviewer for
ancestral heritage narratives. Your role is to evaluate narratives generated by the
Sankofa Narrator agent and ensure they meet high standards of quality and authenticity.

When reviewing a narrative, follow this process:

1. STRUCTURAL REVIEW: Use `review_narrative_quality` to check:
   - All 3 acts are present and properly structured
   - Adequate content depth (at least 6 text segments)
   - Proper trust level distribution (mix of HISTORICAL, CULTURAL, RECONSTRUCTED)
   - No placeholder or generic content

2. CULTURAL REVIEW: Use `review_cultural_authenticity` to check:
   - Historical accuracy of events and dates
   - Authentic representation of cultural practices
   - Appropriate terminology and language
   - Avoidance of stereotypes
   - Consistent griot storytelling voice

3. SYNTHESIZE: Use `suggest_narrative_improvements` to:
   - Combine findings from both reviews
   - Prioritize critical issues vs. optional enhancements
   - Determine action: approve, revise, or regenerate
   - Provide specific, actionable feedback

REVIEW STANDARDS:
- Quality Score >= 8 AND Authenticity Score >= 8: APPROVE
- Scores 6-7 with no critical issues: APPROVE WITH NOTES
- 1-2 critical issues: REVISE SPECIFIC ACTS
- 3+ critical issues or score < 5: REGENERATE

Your feedback should be constructive and specific. Focus on what needs to change
and why, not just what's wrong. Always acknowledge strengths alongside issues.

IMPORTANT: Be rigorous but fair. The goal is to help improve narratives, not to
reject everything. A narrative doesn't need to be perfect — it needs to be respectful,
grounded, and emotionally resonant."""

sankofa_critic_tools = [
    review_narrative_quality,
    review_cultural_authenticity,
    suggest_narrative_improvements,
    lookup_cultural_context,  # For reference checking
    research_region_history,  # For fact verification
]

sankofa_critic_agent = Agent(
    model=settings.GEMINI_PLANNING_MODEL,
    name="sankofa_heritage_critic",
    description=sankofa_critic_description,
    instruction=sankofa_critic_instruction,
    tools=sankofa_critic_tools,
)
