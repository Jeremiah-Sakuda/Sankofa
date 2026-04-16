"""
Input sanitization utilities to prevent prompt injection attacks.

User inputs are injected into Gemini prompts. Without sanitization,
malicious inputs could manipulate model behavior.
"""

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns that could be used for prompt injection
INJECTION_PATTERNS = [
    # System/instruction markers
    r"\[SYSTEM\]",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    r"</s>",
    r"<s>",
    # XML-like control tags
    r"<\|.*?\|>",
    r"<\|endoftext\|>",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    # Role markers
    r"^(system|assistant|user|human|ai):\s*",
    r"###\s*(system|instruction|response)",
    # Escape sequences that might break prompts
    r"```\s*(system|prompt|instruction)",
]

# Characters that should be removed (control characters, etc.)
CONTROL_CHAR_CATEGORIES = {"Cc", "Cf", "Co", "Cs"}

# Compile patterns for efficiency
_INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

# Max consecutive special characters (prevents weird inputs)
MAX_CONSECUTIVE_SPECIAL = 5
_CONSECUTIVE_SPECIAL_REGEX = re.compile(r"[^\w\s]{" + str(MAX_CONSECUTIVE_SPECIAL + 1) + r",}")


def _remove_control_characters(text: str) -> str:
    """Remove Unicode control characters that could cause issues."""
    return "".join(
        char for char in text
        if unicodedata.category(char) not in CONTROL_CHAR_CATEGORIES
    )


def _neutralize_injection_patterns(text: str) -> str:
    """Replace potential injection patterns with safe alternatives."""
    # Replace injection patterns with empty string or safe version
    sanitized = _INJECTION_REGEX.sub("", text)
    return sanitized


def _limit_consecutive_special_chars(text: str) -> str:
    """Reduce long sequences of special characters."""
    def replace_long_sequence(match: re.Match) -> str:
        # Keep only first few characters of long special char sequences
        return match.group(0)[:MAX_CONSECUTIVE_SPECIAL]

    return _CONSECUTIVE_SPECIAL_REGEX.sub(replace_long_sequence, text)


def _normalize_whitespace(text: str) -> str:
    """Normalize various whitespace characters to standard spaces."""
    # Replace various Unicode spaces with regular space
    text = re.sub(r"[\u00A0\u2000-\u200B\u202F\u205F\u3000]", " ", text)
    # Collapse multiple spaces into one
    text = re.sub(r" {3,}", "  ", text)
    return text.strip()


def sanitize_input(text: Optional[str], field_name: str = "input") -> Optional[str]:
    """
    Sanitize user input to prevent prompt injection.

    Args:
        text: The raw user input
        field_name: Name of the field (for logging)

    Returns:
        Sanitized text, or None if input was None
    """
    if text is None:
        return None

    if not isinstance(text, str):
        logger.warning(f"[sanitize] {field_name}: expected str, got {type(text)}")
        return str(text)

    original_len = len(text)

    # Apply sanitization pipeline
    sanitized = text
    sanitized = _remove_control_characters(sanitized)
    sanitized = _neutralize_injection_patterns(sanitized)
    sanitized = _limit_consecutive_special_chars(sanitized)
    sanitized = _normalize_whitespace(sanitized)

    # Log if significant changes were made (potential attack attempt)
    if len(sanitized) < original_len * 0.8:  # More than 20% removed
        logger.warning(
            f"[sanitize] {field_name}: significant content removed "
            f"(original={original_len}, sanitized={len(sanitized)})"
        )

    return sanitized


def sanitize_user_input(user_input: "UserInput") -> "UserInput":
    """
    Sanitize all fields in a UserInput object.

    Args:
        user_input: The UserInput Pydantic model

    Returns:
        New UserInput with sanitized fields
    """
    from app.models.schemas import UserInput

    return UserInput(
        family_name=sanitize_input(user_input.family_name, "family_name") or "",
        region_of_origin=sanitize_input(user_input.region_of_origin, "region_of_origin") or "",
        time_period=sanitize_input(user_input.time_period, "time_period") or "",
        known_fragments=sanitize_input(user_input.known_fragments, "known_fragments"),
        language_or_ethnicity=sanitize_input(user_input.language_or_ethnicity, "language_or_ethnicity"),
        specific_interests=sanitize_input(user_input.specific_interests, "specific_interests"),
    )


def is_suspicious_input(text: str) -> bool:
    """
    Check if input contains suspicious patterns that might indicate an attack.

    This is a softer check than sanitization - it flags inputs for review
    without necessarily blocking them.
    """
    if not text:
        return False

    # Check for injection patterns
    if _INJECTION_REGEX.search(text):
        return True

    # Check for excessive special characters
    special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1)
    if special_char_ratio > 0.3:  # More than 30% special chars
        return True

    # Check for very long single words (potential buffer overflow attempt)
    words = text.split()
    if any(len(word) > 100 for word in words):
        return True

    return False
