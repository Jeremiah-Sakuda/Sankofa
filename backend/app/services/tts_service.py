"""
TTS Service — Generates audio narration using Gemini TTS.
"""

import asyncio
import base64
import io
import logging
import wave
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
                # Wrap PCM in WAV container
                pcm_data = part.inline_data.data
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(pcm_data)
                
                wav_bytes = wav_buffer.getvalue()

                # Log success
                logger.info(
                    "TTS Success: generated %d bytes (WAV) for text '%s...'",
                    len(wav_bytes),
                    text[:30].replace("\n", " "),
                )
                
                b64 = base64.b64encode(wav_bytes).decode("utf-8")
                mime = "audio/wav"
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
