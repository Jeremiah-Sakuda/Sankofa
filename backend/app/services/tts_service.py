"""
TTS Service — Generates audio narration using Gemini TTS.
"""

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


async def generate_narration(text: str, voice_name: str = "Kore") -> str | None:
    """Generate audio narration for a text segment.

    Returns base64-encoded audio data or None if generation fails.
    """
    if not text or len(text.strip()) < 10:
        return None

    try:
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
                        prebuilt_voice_config=PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
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
                    return base64.b64encode(part.inline_data.data).decode("utf-8")

        return None

    except Exception as e:
        logger.warning(f"TTS generation failed: {e}")
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
