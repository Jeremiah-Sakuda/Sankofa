import re
from app.models.schemas import NarrativeSegment

TAG_PATTERN = re.compile(r"\[(HISTORICAL|CULTURAL|RECONSTRUCTED)\]", re.IGNORECASE)

TRUST_LEVELS = {"historical", "cultural", "reconstructed"}


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
