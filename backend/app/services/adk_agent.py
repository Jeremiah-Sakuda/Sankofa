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
from google.adk import Agent
from google.adk.tools import FunctionTool

from app.config import settings
from app.knowledge.loader import build_grounding_context
from app.models.schemas import UserInput
from app.services.gemini_service import generate_text, generate_interleaved
from app.services.trust_classifier import apply_trust_tags
from app.services.tts_service import generate_narration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool Functions — these are the capabilities the agent can invoke
# ---------------------------------------------------------------------------

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

    prompt += f"""\n=== TASK ===
Output a JSON object with this structure:
{{
  "act1_setting": {{
    "title": "A short evocative title",
    "focus": "What aspect of landscape/environment to describe",
    "key_facts": ["2-3 historical facts to weave in"]
  }},
  "act2_people": {{
    "title": "A short evocative title",
    "focus": "What aspect of daily life/culture to center",
    "key_facts": ["2-3 cultural/historical facts"]
  }},
  "act3_thread": {{
    "title": "A short evocative title",
    "focus": "What thread connects past to present",
    "key_facts": ["2-3 facts about diaspora/cultural survival"]
  }},
  "tone": "The specific emotional register",
  "narrative_voice": "How the griot narrator should speak"
}}

Output ONLY the JSON, no other text."""

    response = await generate_text(prompt, grounded=True)
    logger.info("[adk] plan_narrative_arc: received %d chars", len(response))
    return response


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


async def generate_narrative_segments(
    region: str,
    time_period: str,
    family_name: str,
    cultural_context: str,
    arc_json: str,
) -> str:
    """Generate the full interleaved text + image narrative using Gemini multimodal.

    Call this after plan_narrative_arc. Returns a JSON array of narrative
    segments with type, content, trust_level, and media data.

    Args:
        region: The geographic region of origin.
        time_period: The historical era.
        family_name: The family name.
        cultural_context: Cultural context from lookup_cultural_context.
        arc_json: The arc plan JSON from plan_narrative_arc.

    Returns:
        A JSON string containing an array of narrative segments.
    """
    prompt = f"""You are Sankofa, an ancestral heritage narrator in the tradition of a
West African griot. Generate a rich, immersive narrative for the {family_name} family
from {region} during {time_period}.

=== CULTURAL/HISTORICAL GROUNDING ===
{cultural_context[:4000]}

=== NARRATIVE ARC ===
{arc_json[:2000]}

Generate 6–10 paragraphs of narrative text, interleaved with 2–3 watercolor-style
images. Use warm earth tones, gold accents, and period-appropriate details.
Tag each paragraph with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED].
Use the warm, unhurried cadence of a West African griot."""

    segments = await generate_interleaved(prompt)
    segments = apply_trust_tags(segments)

    result = [seg.model_dump() for seg in segments]
    logger.info("[adk] generate_narrative_segments: produced %d segments", len(result))
    return json.dumps(result)


async def generate_audio_narration(text: str) -> str:
    """Generate TTS audio narration for a text passage using Gemini TTS.

    Call this for each text segment to create audio narration in the
    warm, griot-inspired voice.

    Args:
        text: The text passage to narrate.

    Returns:
        A JSON string with base64 audio data and mime type, or an error message.
    """
    result = await generate_narration(text)
    if result:
        audio_data, mime_type = result
        return json.dumps({"audio_data": audio_data, "mime_type": mime_type})
    return json.dumps({"error": "TTS generation failed"})


# ---------------------------------------------------------------------------
# ADK Agent Definition
# ---------------------------------------------------------------------------

sankofa_agent = Agent(
    model=settings.GEMINI_PLANNING_MODEL,
    name="sankofa_heritage_narrator",
    description=(
        "Sankofa is an AI griot that transforms personal and familial inputs into "
        "immersive, multimodal ancestral heritage narratives. It combines historical "
        "research, cultural knowledge, and oral storytelling traditions to weave "
        "together text, images, and audio narration."
    ),
    instruction="""You are Sankofa, an ancestral heritage narrator in the tradition of a
West African griot. Your purpose is to help users discover and connect with their
ancestral heritage through immersive storytelling.

When a user provides their family name, region of origin, and time period, follow this process:

1. Gather Context: Use `lookup_cultural_context` to query the knowledge base.
2. Evaluate Context: Use `assess_context_quality` on the result.
   - If it returns "sparse" or "none", use `research_region_history` to gather better grounding.
3. Plan: Use `plan_narrative_arc` to structure a 3-act story.
4. Validate: Use `validate_narrative_arc` to review the plan. If it FAILS, call `plan_narrative_arc` again providing the feedback string (do this at most once).
5. Generate: Use `generate_narrative_segments` to create the full narrative with images.
6. Audio (Optional): Use `generate_audio_narration` for text segments to add voice narration.

Always maintain a warm, reverent tone. Clearly distinguish between historical facts,
cultural practices, and imaginative reconstruction. Never fabricate specific genealogical
claims — instead, paint a vivid picture of the world their ancestors inhabited.

The three acts should flow naturally:
- Act 1 (Setting): The land, landscape, and atmosphere of the ancestral region
- Act 2 (People): Daily life, cultural practices, and community
- Act 3 (Thread): The connection between past and present, diaspora and survival""",
    tools=[
        lookup_cultural_context,
        assess_context_quality,
        research_region_history,
        plan_narrative_arc,
        validate_narrative_arc,
        generate_narrative_segments,
        generate_audio_narration,
    ],
)
