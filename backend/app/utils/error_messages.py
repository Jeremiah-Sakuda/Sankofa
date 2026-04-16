"""
User-friendly error message translation.

Maps internal exceptions to safe, helpful messages for end users.
Full exception details are logged server-side.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Patterns to detect specific error types from exception messages
_ERROR_PATTERNS = [
    # API key issues
    (r"(?i)(invalid|missing|expired).*api.?key", "SERVICE_UNAVAILABLE"),
    (r"(?i)api.?key.*(invalid|missing|expired)", "SERVICE_UNAVAILABLE"),
    (r"(?i)authentication.*fail", "SERVICE_UNAVAILABLE"),
    (r"(?i)401|403.*unauthorized", "SERVICE_UNAVAILABLE"),

    # Quota/rate limiting
    (r"(?i)quota.*exceed", "RATE_LIMITED"),
    (r"(?i)rate.*limit", "RATE_LIMITED"),
    (r"(?i)too.*many.*requests", "RATE_LIMITED"),
    (r"(?i)429", "RATE_LIMITED"),
    (r"(?i)resource.*exhaust", "RATE_LIMITED"),

    # Model/service issues
    (r"(?i)model.*not.*found", "MODEL_UNAVAILABLE"),
    (r"(?i)model.*not.*support", "MODEL_UNAVAILABLE"),
    (r"(?i)503|502|500.*service", "SERVICE_UNAVAILABLE"),
    (r"(?i)service.*unavailable", "SERVICE_UNAVAILABLE"),
    (r"(?i)internal.*server.*error", "SERVICE_UNAVAILABLE"),

    # Timeout
    (r"(?i)timeout", "TIMEOUT"),
    (r"(?i)timed.*out", "TIMEOUT"),
    (r"(?i)deadline.*exceed", "TIMEOUT"),

    # Network issues
    (r"(?i)connection.*refused", "NETWORK_ERROR"),
    (r"(?i)network.*error", "NETWORK_ERROR"),
    (r"(?i)dns.*fail", "NETWORK_ERROR"),

    # Content safety
    (r"(?i)blocked.*safety", "CONTENT_BLOCKED"),
    (r"(?i)content.*filter", "CONTENT_BLOCKED"),
    (r"(?i)safety.*setting", "CONTENT_BLOCKED"),
]

# User-friendly messages for each error type
_USER_MESSAGES = {
    "SERVICE_UNAVAILABLE": "The griot needs a moment to gather strength. Please try again shortly.",
    "RATE_LIMITED": "The griot is sharing many stories right now. Please wait a moment and try again.",
    "MODEL_UNAVAILABLE": "The griot's voice is temporarily unavailable. Please try again in a few minutes.",
    "TIMEOUT": "The story is taking longer than expected. Please try again.",
    "NETWORK_ERROR": "The connection to the griot was interrupted. Please check your network and try again.",
    "CONTENT_BLOCKED": "The griot cannot weave this particular tale. Please try a different approach.",
    "UNKNOWN": "An unexpected error occurred. Please try again.",
}


def classify_error(exception: Exception) -> str:
    """
    Classify an exception into an error type.

    Args:
        exception: The exception to classify

    Returns:
        Error type string (e.g., "RATE_LIMITED", "TIMEOUT")
    """
    error_str = str(exception).lower()

    # Also check exception class name
    class_name = type(exception).__name__.lower()
    combined = f"{class_name}: {error_str}"

    for pattern, error_type in _ERROR_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return error_type

    return "UNKNOWN"


def get_user_message(exception: Exception) -> str:
    """
    Get a user-friendly error message for an exception.

    The full exception is logged server-side for debugging.

    Args:
        exception: The exception that occurred

    Returns:
        A safe, user-friendly error message
    """
    error_type = classify_error(exception)

    # Log the full error for debugging
    logger.error(
        f"Error classified as {error_type}: {type(exception).__name__}: {exception}",
        exc_info=True
    )

    return _USER_MESSAGES.get(error_type, _USER_MESSAGES["UNKNOWN"])


def translate_error_for_sse(exception: Exception) -> dict:
    """
    Create an SSE-compatible error event with a user-friendly message.

    Args:
        exception: The exception that occurred

    Returns:
        Dict suitable for SSE event: {"error": "user-friendly message"}
    """
    return {"error": get_user_message(exception)}
