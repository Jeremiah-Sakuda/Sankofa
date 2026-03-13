"""
Narrative Planner — 3-step prompt chain:
1. Context Assembly (knowledge base grounding)
2. Arc Planning (3-act structure outline via text-only Gemini)
3. Interleaved Generation (text + image via Gemini multimodal)
"""

import json
import logging
from app.models.schemas import UserInput, NarrativeSegment
from app.models.session import Session
from app.knowledge.loader import build_grounding_context
from app.services.gemini_service import generate_text, generate_interleaved
from app.services.trust_classifier import apply_trust_tags

logger = logging.getLogger(__name__)


async def plan_and_generate(session: Session) -> list[NarrativeSegment]:
    """Execute the full 3-step narrative pipeline."""
    arc, context = await plan_arc_only(session)
    return await generate_narrative_only(session, context)


# Cap context size per step to reduce prompt size and speed up Gemini calls
ARC_CONTEXT_MAX_CHARS = 1500   # Keep arc prompt small so the first Gemini call is fast
NARRATIVE_CONTEXT_MAX_CHARS = 4000  # Narrative can use more for accuracy


def get_fast_arc(session: Session) -> tuple[dict, str]:
    """Build grounding context and use a template arc (no Gemini call). Use for fast mode."""
    user_input = session.user_input
    grounding_context_full = build_grounding_context(user_input)
    arc = _fallback_arc(user_input)
    session.arc_outline = arc
    return arc, grounding_context_full


def _cap_context(context: str, max_chars: int) -> str:
    if len(context) <= max_chars:
        return context
    return context[: max_chars].rsplit("\n", 1)[0] + "\n\n[... context truncated for length ...]"


async def plan_arc_only(session: Session) -> tuple[dict, str]:
    """Step 1 + 2: Build grounding context and plan arc via Gemini. Returns (arc_outline, grounding_context)."""
    user_input = session.user_input

    logger.info("[narrative] Step 1: Assembling grounding context...")
    grounding_context_full = build_grounding_context(user_input)
    grounding_context = _cap_context(grounding_context_full, ARC_CONTEXT_MAX_CHARS)
    logger.info(f"[narrative] Step 1 done: context {len(grounding_context_full)} chars (using {len(grounding_context)} for arc)")

    logger.info("[narrative] Step 2: Planning arc (calling Gemini text model)...")
    arc_outline = await _plan_arc(user_input, grounding_context)
    session.arc_outline = arc_outline
    logger.info(f"[narrative] Step 2 done: arc planned ({json.dumps(arc_outline)[:120]}...)")
    # Return full context for narrative step (we'll cap again there for the prompt)
    return arc_outline, grounding_context_full


async def generate_narrative_only(session: Session, grounding_context: str) -> list[NarrativeSegment]:
    """Step 3: Generate interleaved text + images via Gemini."""
    user_input = session.user_input
    arc_outline = session.arc_outline or {}

    logger.info("[narrative] Step 3: Generating interleaved narrative (calling Gemini image model)...")
    segments = await _generate_narrative(user_input, grounding_context, arc_outline)
    logger.info(f"[narrative] Step 3 done: generated {len(segments)} segments")

    segments = apply_trust_tags(segments)
    _assign_acts(segments)
    return segments


async def _plan_arc(user_input: UserInput, context: str) -> dict:
    """Step 2: Generate a narrative arc outline using text-only Gemini."""
    prompt = f"""You are a narrative architect planning an ancestral heritage story.

Given the following cultural and historical context about {user_input.region_of_origin}
during {user_input.time_period}, plan a three-act narrative structure for the
{user_input.family_name} family heritage story.

=== GROUNDING CONTEXT ===
{context}

=== TASK ===
Output a JSON object with this exact structure:
{{
  "act1_setting": {{
    "title": "A short evocative title for the opening",
    "focus": "What specific aspect of the landscape/environment to describe",
    "image_prompt": "A detailed prompt for a watercolor-style landscape image",
    "key_facts": ["2-3 historical facts to weave in"],
    "ambient_track": "Must be exactly one of: fire.wav, wind.wav, nature.wav, market.wav, drums.wav"
  }},
  "act2_people": {{
    "title": "A short evocative title for the people section",
    "focus": "What aspect of daily life/culture to center",
    "image_prompt": "A detailed prompt for a portrait-style image of people",
    "key_facts": ["2-3 cultural/historical facts to weave in"],
    "ambient_track": "Must be exactly one of: fire.wav, wind.wav, nature.wav, market.wav, drums.wav"
  }},
  "act3_thread": {{
    "title": "A short evocative title for the connection section",
    "focus": "What thread connects past to present",
    "image_prompt": "A detailed prompt for an image bridging past and present",
    "key_facts": ["2-3 facts about diaspora/migration/cultural survival"],
    "ambient_track": "Must be exactly one of: fire.wav, wind.wav, nature.wav, market.wav, drums.wav"
  }},
  "tone": "The specific emotional register (e.g., 'reverent and warm', 'bittersweet but hopeful')",
  "narrative_voice": "How the griot narrator should speak to this specific listener"
}}

Output ONLY the JSON, no other text."""

    response = await generate_text(prompt, grounded=True)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse arc outline, using fallback")
        return _fallback_arc(user_input)


def _fallback_arc(user_input: UserInput) -> dict:
    """Fallback arc when JSON parsing fails."""
    return {
        "act1_setting": {
            "title": f"The Land of the {user_input.family_name}",
            "focus": f"The landscape and atmosphere of {user_input.region_of_origin} during {user_input.time_period}",
            "image_prompt": f"Watercolor illustration of {user_input.region_of_origin} landscape, {user_input.time_period}, warm earth tones, golden hour light",
            "key_facts": [],
            "ambient_track": "wind.wav",
        },
        "act2_people": {
            "title": "The People and Their Ways",
            "focus": "Daily life, cultural practices, and community",
            "image_prompt": f"Watercolor portrait of people in {user_input.region_of_origin}, {user_input.time_period}, traditional dress, warm tones",
            "key_facts": [],
            "ambient_track": "market.wav",
        },
        "act3_thread": {
            "title": "The Thread That Reaches You",
            "focus": "Migration, cultural survival, and connection to the present",
            "image_prompt": f"Watercolor illustration bridging {user_input.region_of_origin} heritage to modern diaspora life, warm earth tones",
            "key_facts": [],
            "ambient_track": "drums.wav",
        },
        "tone": "warm and reverent",
        "narrative_voice": "a griot speaking with warmth and gravity",
    }


async def _generate_narrative(
    user_input: UserInput, context: str, arc: dict
) -> list[NarrativeSegment]:
    """Step 3: Generate the full interleaved narrative."""
    context_capped = _cap_context(context, NARRATIVE_CONTEXT_MAX_CHARS)
    act1 = arc.get("act1_setting", {})
    act2 = arc.get("act2_people", {})
    act3 = arc.get("act3_thread", {})
    tone = arc.get("tone", "warm and reverent")
    voice = arc.get("narrative_voice", "a griot narrator")

    prompt = f"""You are Sankofa, an ancestral heritage narrator in the tradition of the West African griot.
You speak with the voice of {voice}. Your tone is {tone}.

You are telling the heritage story of the {user_input.family_name} family from
{user_input.region_of_origin} during {user_input.time_period}.

=== GROUNDING CONTEXT (use these facts to ensure accuracy) ===
{context_capped}

=== NARRATIVE ARC ===

ACT 1: "{act1.get('title', 'Setting the World')}"
Focus: {act1.get('focus', 'the landscape and environment')}
Generate a watercolor-style landscape image: {act1.get('image_prompt', '')}
Key facts to weave in: {', '.join(act1.get('key_facts', []))}

Write 2-3 rich paragraphs establishing the world. Use vivid sensory detail —
the smell of the earth, the sound of the market, the quality of the light.
Prepend each paragraph with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED].

ACT 2: "{act2.get('title', 'The People and Their Lives')}"
Focus: {act2.get('focus', 'daily life and cultural practices')}
Generate a portrait-style image: {act2.get('image_prompt', '')}
Key facts to weave in: {', '.join(act2.get('key_facts', []))}

Write 2-3 paragraphs about daily life, occupations, cultural practices, and
the specific role the family context suggests. Make the listener feel present.
Prepend each paragraph with the appropriate trust tag.

ACT 3: "{act3.get('title', 'The Thread to You')}"
Focus: {act3.get('focus', 'connection to present')}
Generate a bridging image: {act3.get('image_prompt', '')}
Key facts to weave in: {', '.join(act3.get('key_facts', []))}

Write 2-3 paragraphs connecting the historical narrative to the present day.
Discuss migration, cultural survivals, traditions that persist. End with a
reflective moment directed to the listener. Prepend each paragraph.

=== CRITICAL INSTRUCTIONS ===
- Generate exactly 3 images total, one for each act
- Write in a warm, unhurried oral storytelling voice — as if by firelight
- Every paragraph MUST start with [HISTORICAL], [CULTURAL], or [RECONSTRUCTED]
- Use [HISTORICAL] for documented facts, [CULTURAL] for attested practices,
  [RECONSTRUCTED] for imaginative reconstruction
- Images should be watercolor illustration style with warm earth tones
- No modern anachronisms in images
- Do NOT fabricate specific genealogical claims
- Use sensory detail: sounds, smells, textures, light quality"""

    return await generate_interleaved(prompt)


def _assign_acts(segments: list[NarrativeSegment]) -> None:
    """Assign act numbers to segments based on content cues."""
    act = 1
    image_count = 0

    for seg in segments:
        if seg.type == "image":
            image_count += 1
            if image_count == 1:
                seg.is_hero = True

        if seg.type == "text" and seg.content:
            content_upper = seg.content.upper()
            if any(
                marker in content_upper
                for marker in ["ACT 2", "ACT TWO", "PEOPLE AND THEIR", "DAILY LIFE"]
            ):
                act = 2
            elif any(
                marker in content_upper
                for marker in ["ACT 3", "ACT THREE", "THREAD TO YOU", "THREAD THAT", "PRESENT DAY", "TODAY"]
            ):
                act = 3

        if image_count == 2 and act < 2:
            act = 2
        elif image_count == 3 and act < 3:
            act = 3

        seg.act = act
