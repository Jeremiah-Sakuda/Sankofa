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
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.schemas import NarrativeSegment
from app.services.gemini_service import _is_transient, get_client

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent TTS API calls across all sessions
# Prevents overwhelming Gemini TTS quota during high load
_TTS_CONCURRENCY_LIMIT = 4
_tts_semaphore: asyncio.Semaphore | None = None


def _get_tts_semaphore() -> asyncio.Semaphore:
    """Get or create the TTS semaphore (must be called from async context)."""
    global _tts_semaphore
    if _tts_semaphore is None:
        _tts_semaphore = asyncio.Semaphore(_TTS_CONCURRENCY_LIMIT)
    return _tts_semaphore

# ---------------------------------------------------------------------------
# Sentence-level splitting
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+(?=\[A-Z"\u201C])')

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

@retry(
    retry=retry_if_exception(_is_transient),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
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
    """Non-blocking wrapper around the synchronous PCM generator.

    Uses a semaphore to limit concurrent TTS API calls globally.
    """
    semaphore = _get_tts_semaphore()
    try:
        async with semaphore:
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
        api_results = await asyncio.gather(
            *[_generate_pcm_async(chunk, voice_name) for chunk in chunks]
        )

        def _extract_pcm(data: bytes) -> bytes:
            """Extract pure PCM frames, stripping WAV headers if present."""
            try:
                with wave.open(io.BytesIO(data), 'rb') as w:
                    return w.readframes(w.getnframes())
            except wave.Error:
                return data  # Fallback if it's already raw PCM

        pcm_parts = [_extract_pcm(r) for r in api_results if r is not None]

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


def spawn_tts_task(
    seg: NarrativeSegment,
    tts_queue: asyncio.Queue,
) -> "asyncio.Task[None]":
    """Spawn a background TTS task that places an audio NarrativeSegment into *tts_queue*.

    The caller is responsible for appending the returned task to a tracking list and
    draining *tts_queue* on subsequent event loop iterations.
    """
    async def _do_tts() -> None:
        try:
            result = await generate_narration(seg.content)
            if result:
                audio_data, mime = result
                await tts_queue.put(
                    NarrativeSegment(
                        type="audio",
                        content=(seg.content[:100] if seg.content else ""),
                        media_data=audio_data,
                        media_type=mime,
                        trust_level=seg.trust_level,
                        sequence=seg.sequence,
                        act=seg.act,
                    )
                )
        except Exception as exc:
            logger.warning("[tts] TTS task failed: %s", exc)

    return asyncio.create_task(_do_tts())


async def generate_narration_for_segments(segments: list, voice_name: str = "Kore") -> list:
    """Generate audio for all text segments, mutating them in place."""
    for seg in segments:
        if seg.type == "text" and seg.content:
            audio_data = await generate_narration(seg.content, voice_name)
            if audio_data:
                seg.media_data = audio_data
                seg.media_type = "audio/wav"
    return segments
