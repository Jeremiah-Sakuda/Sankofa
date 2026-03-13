"""
TTS Service — Generates audio narration using Gemini TTS.
"""

import asyncio
import base64
import logging
from google.genai.types import (
    GenerateContentConfig,
    Modality,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)
from app.services.gemini_service import get_client
from app.config import settings

logger = logging.getLogger(__name__)


def _generate_narration_sync(text: str, voice_name: str) -> tuple[str, str] | None:
    """Synchronous TTS call (run in thread pool)."""
    client = get_client()
    response = client.models.generate_content(
        model=settings.GEMINI_TTS_MODEL,
        contents=f"""Read the following passage aloud in the warm, unhurried cadence
of a West African griot — resonant, deep, with occasional pauses for emphasis.
Let the words breathe. This is oral storytelling, not news reading.

{text}""",
        config=GenerateContentConfig(
            response_modalities=[Modality.AUDIO],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice_name),
                )
            ),
        ),
    )
    if (
        response.candidates
        and response.candidates[0].content
        and response.candidates[0].content.parts
    ):
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                # Log success
                logger.info(
                    "TTS Success: generated %d bytes for text '%s...'",
                    len(part.inline_data.data),
                    text[:30].replace("\n", " "),
                )
                b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime = getattr(part.inline_data, "mime_type", None) or "audio/wav"
                return (b64, mime)
    return None


async def generate_narration(text: str, voice_name: str = "Kore") -> tuple[str, str] | None:
    """Generate audio narration for a text segment (non-blocking). Returns (base64_data, mime_type) or None."""
    if not text or len(text.strip()) < 10:
        return None
    try:
        return await asyncio.to_thread(_generate_narration_sync, text, voice_name)
    except Exception as e:
        logger.warning("TTS generation failed: %s", e, exc_info=True)
        return None


async def generate_narration_for_segments(segments: list, voice_name: str = "Kore") -> list:
    """Generate audio for all text segments, mutating them in place."""
    for seg in segments:
        if seg.type == "text" and seg.content:
            audio_data = await generate_narration(seg.content, voice_name)
            if audio_data:
                seg.media_data = audio_data
                seg.media_type = "audio/wav"
    return segments
