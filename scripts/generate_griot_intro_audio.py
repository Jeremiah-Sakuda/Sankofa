"""
Generate static griot intro audio assets using Gemini TTS.

Produces two WAV files:
  1. griot-intro.wav  — Full intro monologue (~90-100s)
  2. griot-ready.wav  — "Your story is ready. Come, let us begin." (~5s)

These are static assets committed to the repo. No runtime TTS cost.

Usage:
  cd backend
  python -m scripts.generate_griot_intro_audio

Or from repo root:
  python scripts/generate_griot_intro_audio.py
"""

import asyncio
import io
import os
import sys
import wave

# Ensure backend is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from app.services.tts_service import _generate_pcm_sync, split_for_tts

OUTPUT_DIR = os.path.join(REPO_ROOT, "frontend", "public", "audio")
VOICE = "Kore"

INTRO_TEXT = """\
Come. Sit with me.
I am a griot — a keeper of the stories that time tries to scatter. For generations, my kind have held the memories of families, of kingdoms, of journeys no map could ever trace.
Tonight, I reach back for you.
The Akan people have a word — Sankofa. It means: go back and get it. It teaches us that the past is not behind us. It walks beside us, whispering in the language of our grandmothers, humming in the rhythms our hands remember but our minds have forgotten.
Every family has a thread that stretches back — through oceans crossed and borders redrawn, through languages that changed shape but never lost their meaning. Some of those threads are written in books. Others live only in the land itself, in the rhythm of a song, in the way a name is spoken.
Your ancestors lived. They loved. They built. They endured. And their story did not end — it has been waiting, patient as the baobab, for someone to come and listen.
So let me gather the threads now. Let me listen to what the land remembers, what the old songs still carry. I will weave it all together — and you will hear your heritage, as it was meant to be told.\
"""

READY_TEXT = "Your story is ready. Come, let us begin."


def _extract_pcm(data: bytes) -> bytes:
    """Extract raw PCM frames, stripping WAV headers if present."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            return w.readframes(w.getnframes())
    except wave.Error:
        return data


def _pcm_to_wav_file(pcm_data: bytes, path: str) -> None:
    """Write raw PCM bytes as a mono 24kHz 16-bit WAV file."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_data)


async def generate_wav(text: str, output_path: str) -> None:
    """Split text into chunks, generate TTS concurrently, concatenate into WAV."""
    chunks = split_for_tts(text, max_sentences=2)
    print(f"  Generating {len(chunks)} chunk(s)...")

    async def gen_chunk(i: int, chunk: str) -> bytes | None:
        print(f"    Chunk {i + 1}/{len(chunks)}: {chunk[:50]}...")
        try:
            result = await asyncio.to_thread(_generate_pcm_sync, chunk, VOICE)
            if result:
                print(f"    Chunk {i + 1} done ({len(result)} bytes)")
            else:
                print(f"    Chunk {i + 1} returned no data")
            return result
        except Exception as e:
            print(f"    Chunk {i + 1} failed: {e}")
            return None

    results = await asyncio.gather(*[gen_chunk(i, c) for i, c in enumerate(chunks)])

    pcm_parts = [_extract_pcm(r) for r in results if r is not None]
    if not pcm_parts:
        print(f"  ERROR: No chunks succeeded for {output_path}")
        return

    combined = b"".join(pcm_parts)
    _pcm_to_wav_file(combined, output_path)
    size_kb = os.path.getsize(output_path) / 1024
    duration_s = len(combined) / (24000 * 2)  # 24kHz, 16-bit mono
    print(f"  -> {output_path} ({size_kb:.0f} KB, {duration_s:.1f}s)")


async def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating griot-intro.wav (full monologue)...")
    await generate_wav(INTRO_TEXT, os.path.join(OUTPUT_DIR, "griot-intro.wav"))

    print("\nGenerating griot-ready.wav (transition line)...")
    await generate_wav(READY_TEXT, os.path.join(OUTPUT_DIR, "griot-ready.wav"))

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
