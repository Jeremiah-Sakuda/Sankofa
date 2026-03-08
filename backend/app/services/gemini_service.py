import asyncio
import base64
import logging
from google import genai
from google.genai.types import GenerateContentConfig, Modality
from app.config import settings
from app.models.schemas import NarrativeSegment

logger = logging.getLogger(__name__)

# User-friendly messages when the API returns common errors
API_KEY_ERROR_MSG = (
    "Invalid or missing Google API key. Get a key at https://aistudio.google.com/apikey, "
    "set GOOGLE_API_KEY in backend/.env, then restart the backend."
)
MODEL_NOT_FOUND_MSG = (
    "Model not found or not supported. See https://ai.google.dev/gemini-api/docs/models"
)
def _text_only_model_msg() -> str:
    return (
        f"Model '{settings.GEMINI_IMAGE_MODEL}' only supports text output. "
        "In backend/.env set GEMINI_IMAGE_MODEL=gemini-2.5-flash-image (or remove that line to use the default). Then restart the backend."
    )


def _raise_if_api_key_error(e: Exception) -> None:
    """Only replace with API key message when Google explicitly says the key is invalid."""
    msg = str(e).lower()
    # Match only clear API-key errors (e.g. "API key not valid", reason=API_KEY_INVALID)
    if "api_key_invalid" in msg or ("api key" in msg and "not valid" in msg):
        raise ValueError(API_KEY_ERROR_MSG) from e


def _raise_if_model_not_found(e: Exception) -> None:
    """If this looks like 404 model not found, raise a clear message instead."""
    msg = str(e).lower()
    if "not found" in msg or "404" in msg:
        raise ValueError(MODEL_NOT_FOUND_MSG) from e


def _raise_if_text_only_model(e: Exception) -> None:
    """When the model doesn't support image output (e.g. gemini-2.5-flash used for narrative)."""
    msg = str(e).lower()
    if "only supports text" in msg or "text output" in msg:
        raise ValueError(_text_only_model_msg()) from e


def _get_client() -> genai.Client:
    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        return genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )
    key = settings.GOOGLE_API_KEY
    if not key:
        logger.warning("[gemini] GOOGLE_API_KEY is empty; requests will fail")
    else:
        logger.info("[gemini] Using Gemini API key (length %d). Source: aistudio.google.com/apikey", len(key))
    return genai.Client(api_key=key)


_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


# Model that supports image+text output; use when env has a text-only model
IMAGE_CAPABLE_MODEL = "gemini-2.5-flash-image"
TEXT_ONLY_MODEL_IDS = ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro")


def _generate_interleaved_sync(prompt: str) -> list[NarrativeSegment]:
    """Synchronous Gemini call (run in thread pool)."""
    model = (settings.GEMINI_IMAGE_MODEL or "").strip()
    # If env has a text-only model, use image-capable model so narrative can return images
    if model in TEXT_ONLY_MODEL_IDS or not model:
        logger.info("[gemini] GEMINI_IMAGE_MODEL=%s is text-only; using %s for narrative", model or "(empty)", IMAGE_CAPABLE_MODEL)
        model = IMAGE_CAPABLE_MODEL
    else:
        logger.info("[gemini] Calling Gemini (model=%s) for interleaved text+image...", model)
    try:
        client = get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=[Modality.TEXT, Modality.IMAGE],
                temperature=0.9,
            ),
        )
    except Exception as e:
        logger.error("[gemini] Gemini image model call failed: %s", e, exc_info=True)
        _raise_if_api_key_error(e)
        _raise_if_model_not_found(e)
        _raise_if_text_only_model(e)
        raise
    segments: list[NarrativeSegment] = []
    sequence = 0
    if not response.candidates or not response.candidates[0].content:
        logger.warning("[gemini] Gemini returned no candidates (check API key and model access)")
        return segments
    logger.info("[gemini] Gemini image model returned successfully")
    for part in response.candidates[0].content.parts:
        if part.text:
            segments.append(
                NarrativeSegment(
                    type="text",
                    content=part.text,
                    trust_level="reconstructed",
                    sequence=sequence,
                )
            )
            sequence += 1
        elif part.inline_data and part.inline_data.data:
            image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
            segments.append(
                NarrativeSegment(
                    type="image",
                    media_data=image_b64,
                    media_type=part.inline_data.mime_type or "image/png",
                    trust_level="reconstructed",
                    sequence=sequence,
                )
            )
            sequence += 1
    return segments


async def generate_interleaved(prompt: str) -> list[NarrativeSegment]:
    """Generate interleaved text + image content from Gemini (non-blocking)."""
    return await asyncio.to_thread(_generate_interleaved_sync, prompt)


def _generate_text_sync(prompt: str, model: str) -> str:
    """Synchronous Gemini text call (run in thread pool)."""
    logger.info("[gemini] Calling Gemini (text model: %s) for arc planning...", model)
    try:
        client = get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(temperature=0.7),
        )
    except Exception as e:
        logger.error("[gemini] Gemini text model call failed: %s", e, exc_info=True)
        _raise_if_api_key_error(e)
        _raise_if_model_not_found(e)
        raise
    if not response.candidates or not response.candidates[0].content:
        logger.warning("[gemini] Gemini text model returned no candidates")
        return ""
    parts = response.candidates[0].content.parts
    if not parts:
        return ""
    logger.info("[gemini] Gemini text model returned successfully")
    return parts[0].text or ""


async def generate_text(prompt: str, model: str | None = None) -> str:
    """Generate text-only content from Gemini (non-blocking)."""
    target_model = model or settings.GEMINI_PLANNING_MODEL
    return await asyncio.to_thread(_generate_text_sync, prompt, target_model)
