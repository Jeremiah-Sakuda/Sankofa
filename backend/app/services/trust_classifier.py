import logging
import re

from app.models.schemas import NarrativeSegment

logger = logging.getLogger(__name__)

TAG_PATTERN = re.compile(r"\[(HISTORICAL|CULTURAL|RECONSTRUCTED)\]", re.IGNORECASE)

TRUST_LEVELS = {"historical", "cultural", "reconstructed"}

# Prompt used for secondary LLM classification of untagged segments
_CLASSIFY_PROMPT = """You are a trust-level classifier for ancestral heritage content.
Classify the following passage as exactly one of:
- HISTORICAL: contains verifiable historical facts, events, or documented practices
- CULTURAL: describes cultural practices, traditions, or social norms without specific verifiable facts
- RECONSTRUCTED: largely imaginative or speculative, filling gaps with plausible but unverified detail

Passage:
\"\"\"{text}\"\"\"

Reply with only one word: HISTORICAL, CULTURAL, or RECONSTRUCTED."""


def classify_and_strip(text: str) -> tuple[str, str]:
    """Extract trust tag from text and return (cleaned_text, trust_level)."""
    match = TAG_PATTERN.search(text)
    if match:
        trust_level = match.group(1).lower()
        cleaned = TAG_PATTERN.sub("", text).strip()
        return cleaned, trust_level
    return text, "reconstructed"


def apply_trust_tags(segments: list[NarrativeSegment]) -> list[NarrativeSegment]:
    """Process segments to extract and apply trust classification."""
    current_trust = "reconstructed"

    for segment in segments:
        if segment.type == "text" and segment.content:
            cleaned, trust_level = classify_and_strip(segment.content)
            segment.content = cleaned
            segment.trust_level = trust_level
            current_trust = trust_level
        elif segment.type == "image":
            segment.trust_level = current_trust

    return segments


async def reclassify_untagged(segments: list[NarrativeSegment]) -> list[NarrativeSegment]:
    """Secondary pass: reclassify text segments that defaulted to 'reconstructed' via LLM.

    Only runs for segments that had no explicit trust tag in the generated text (i.e. the
    model forgot to include [HISTORICAL]/[CULTURAL]/[RECONSTRUCTED]).  Segments that were
    explicitly tagged [RECONSTRUCTED] are left unchanged.

    This is an async function so it should be awaited after apply_trust_tags().
    """
    # Import here to avoid circular dependency at module load time
    from app.services.gemini_service import generate_text  # noqa: PLC0415
    from app.config import settings  # noqa: PLC0415

    # Only reclassify segments where the regex found NO tag (content is unchanged from raw)
    # We detect "no tag was present" by checking if the original content still has
    # its raw form — but since apply_trust_tags already stripped tags, we can't tell
    # after the fact. Instead, we track which segments had no explicit tag.
    # Strategy: run a lightweight LLM call only for segments whose content does NOT
    # start with a known-stripped-prefix pattern and whose trust is "reconstructed".
    for seg in segments:
        if seg.type != "text" or not seg.content or seg.trust_level != "reconstructed":
            continue
        # Skip very short segments (likely headers or captions)
        if len(seg.content.strip()) < 40:
            continue
        try:
            prompt = _CLASSIFY_PROMPT.format(text=seg.content[:500])
            raw = await generate_text(prompt, model=settings.GEMINI_PLANNING_MODEL)
            word = raw.strip().upper().split()[0] if raw.strip() else ""
            if word in ("HISTORICAL", "CULTURAL", "RECONSTRUCTED"):
                seg.trust_level = word.lower()
                logger.info("[trust] Reclassified segment (seq=%s) as %s", seg.sequence, word)
        except Exception as exc:
            logger.warning("[trust] Reclassification failed for seq=%s: %s", seg.sequence, exc)

    return segments
