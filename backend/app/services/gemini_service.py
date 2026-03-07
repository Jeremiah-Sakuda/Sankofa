import asyncio
import base64
import logging
from google import genai
from google.genai.types import GenerateContentConfig, Modality
from app.config import settings
from app.models.schemas import NarrativeSegment

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        return genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def _generate_interleaved_sync(prompt: str) -> list[NarrativeSegment]:
    """Synchronous Gemini call (run in thread pool)."""
    client = get_client()
    response = client.models.generate_content(
        model=settings.GEMINI_IMAGE_MODEL,
        contents=prompt,
        config=GenerateContentConfig(
            response_modalities=[Modality.TEXT, Modality.IMAGE],
            temperature=0.9,
        ),
    )
    segments: list[NarrativeSegment] = []
    sequence = 0
    if not response.candidates or not response.candidates[0].content:
        logger.warning("Gemini returned no candidates")
        return segments
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
    client = get_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=GenerateContentConfig(temperature=0.7),
    )
    if not response.candidates or not response.candidates[0].content:
        return ""
    parts = response.candidates[0].content.parts
    if not parts:
        return ""
    return parts[0].text or ""


async def generate_text(prompt: str, model: str | None = None) -> str:
    """Generate text-only content from Gemini (non-blocking)."""
    target_model = model or settings.GEMINI_PLANNING_MODEL
    return await asyncio.to_thread(_generate_text_sync, prompt, target_model)
