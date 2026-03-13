"""
TTS Service — Generates audio narration using Gemini TTS.

Splits long text into sentence-level chunks for faster generation,
processes sub-chunks concurrently, and concatenates the PCM audio.
"""

import asyncio
import base64
import io
import logging
import re
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

# ---------------------------------------------------------------------------
# Sentence-level splitting
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\u201C])')

def split_for_tts(text: str, max_sentences: int = 3) -> list[str]:
    """Split *text* on sentence boundaries into chunks of up to *max_sentences*.

    Returns a list of non-empty strings. Very short texts (< 2 sentences)
    are returned as a single chunk.
    """
    sentences = _SENTENCE_RE.split(text.strip())
    if len(sentences) <= max_sentences:
        return [text.strip()]
    chunks: list[str] = []
    for i in range(0, len(sentences), max_sentences):
        chunk = " ".join(sentences[i : i + max_sentences]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks if chunks else [text.strip()]


# ---------------------------------------------------------------------------
# Low-level TTS: single chunk → raw PCM bytes
# ---------------------------------------------------------------------------

def _generate_pcm_sync(text: str, voice_name: str) -> bytes | None:
    """Call Gemini TTS for a single text chunk and return raw PCM bytes."""
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
                return part.inline_data.data
    return None


async def _generate_pcm_async(text: str, voice_name: str) -> bytes | None:
    """Non-blocking wrapper around the synchronous PCM generator."""
    try:
        return await asyncio.to_thread(_generate_pcm_sync, text, voice_name)
    except Exception as e:
        logger.warning("TTS chunk failed: %s", e, exc_info=True)
        return None


def _pcm_to_wav_b64(pcm_data: bytes) -> tuple[str, str]:
    """Wrap raw PCM bytes in a WAV container and return (base64, mime)."""
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_data)
    wav_bytes = wav_buffer.getvalue()
    return base64.b64encode(wav_bytes).decode("utf-8"), "audio/wav"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_narration(text: str, voice_name: str = "Kore") -> tuple[str, str] | None:
    """Generate audio narration for a text segment (non-blocking).

    Long text is split into sentence-level chunks, generated concurrently,
    and the resulting PCM data is concatenated into a single WAV.

    Returns (base64_data, mime_type) or None.
    """
    if not text or len(text.strip()) < 10:
        return None

    chunks = split_for_tts(text)
    logger.info(
        "TTS: splitting text (%d chars) into %d chunk(s) for '%s...'",
        len(text), len(chunks), text[:30].replace("\n", " "),
    )

    try:
        # Generate all chunks concurrently
        pcm_results = await asyncio.gather(
            *[_generate_pcm_async(chunk, voice_name) for chunk in chunks]
        )

        # Concatenate successful PCM results in order
        pcm_parts = [r for r in pcm_results if r is not None]
        if not pcm_parts:
            logger.warning("TTS: no chunks succeeded for '%s...'", text[:30])
            return None

        combined_pcm = b"".join(pcm_parts)

        logger.info(
            "TTS Success: %d/%d chunks, %d bytes PCM for '%s...'",
            len(pcm_parts), len(chunks), len(combined_pcm),
            text[:30].replace("\n", " "),
        )

        return _pcm_to_wav_b64(combined_pcm)

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
