"""
Generate static griot intro assets using Gemini APIs.

Audio (Gemini TTS):
  1. griot-intro.wav  — Full intro monologue (~90-100s)
  2. griot-ready.wav  — "Your story is ready. Come, let us begin." (~5s)

Images (Gemini Image):
  5 atmospheric watercolor-style images for the intro background.

These are static assets committed to the repo. No runtime cost.

Usage (from repo root):
  python scripts/generate_griot_intro_assets.py
  python scripts/generate_griot_intro_assets.py --images-only
  python scripts/generate_griot_intro_assets.py --audio-only
"""

import argparse
import asyncio
import base64
import io
import os
import sys
import wave

# Ensure backend is importable
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from app.services.tts_service import _generate_pcm_sync, split_for_tts

AUDIO_OUTPUT_DIR = os.path.join(REPO_ROOT, "frontend", "public", "audio")
IMAGE_OUTPUT_DIR = os.path.join(REPO_ROOT, "frontend", "public", "images", "intro")
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

IMAGE_PROMPTS = [
    (
        "baobab.png",
        "Watercolor illustration of a majestic baobab tree at golden hour on the African savanna, "
        "warm earth tones, soft amber light, painterly brushstrokes, no text or words",
    ),
    (
        "griot.png",
        "Watercolor painting of a West African griot storyteller seated by firelight, "
        "warm amber and deep umber tones, intimate atmosphere, painterly style, no text or words",
    ),
    (
        "ocean.png",
        "Watercolor seascape at dawn, vast ocean with distant horizon, "
        "warm golden light reflecting on water, earth tones, contemplative mood, painterly brushstrokes, no text or words",
    ),
    (
        "village.png",
        "Watercolor illustration of a traditional West African village gathering under a large tree, "
        "warm earth tones, golden light, sense of community, painterly style, no text or words",
    ),
    (
        "threads.png",
        "Watercolor abstract of golden threads weaving together against a deep umber background, "
        "warm tones, heritage motif, painterly brushstrokes, no text or words",
    ),
]


# ---------------------------------------------------------------------------
# Audio generation
# ---------------------------------------------------------------------------

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
    duration_s = len(combined) / (24000 * 2)
    print(f"  -> {output_path} ({size_kb:.0f} KB, {duration_s:.1f}s)")


async def generate_audio() -> None:
    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    print("=== Generating audio assets ===\n")

    print("Generating griot-intro.wav (full monologue)...")
    await generate_wav(INTRO_TEXT, os.path.join(AUDIO_OUTPUT_DIR, "griot-intro.wav"))

    print("\nGenerating griot-ready.wav (transition line)...")
    await generate_wav(READY_TEXT, os.path.join(AUDIO_OUTPUT_DIR, "griot-ready.wav"))


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------

def _generate_image_sync(prompt: str) -> bytes | None:
    """Call Gemini image model to generate a single image. Returns PNG bytes."""
    from google.genai.types import GenerateContentConfig, Modality

    from app.config import settings
    from app.services.gemini_service import get_client

    client = get_client()
    model = settings.GEMINI_IMAGE_MODEL

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=GenerateContentConfig(
            response_modalities=[Modality.IMAGE],
            temperature=0.9,
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


async def generate_images() -> None:
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)
    print("\n=== Generating image assets ===\n")

    for filename, prompt in IMAGE_PROMPTS:
        output_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
        print(f"Generating {filename}...")
        try:
            result = await asyncio.to_thread(_generate_image_sync, prompt)
            if result:
                # result may be raw bytes (PNG) — write directly
                with open(output_path, "wb") as f:
                    f.write(result)
                size_kb = os.path.getsize(output_path) / 1024
                print(f"  -> {output_path} ({size_kb:.0f} KB)")
            else:
                print(f"  ERROR: No image data returned for {filename}")
        except Exception as e:
            print(f"  ERROR generating {filename}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate griot intro assets")
    parser.add_argument("--audio-only", action="store_true", help="Only generate audio files")
    parser.add_argument("--images-only", action="store_true", help="Only generate image files")
    args = parser.parse_args()

    if args.audio_only:
        await generate_audio()
    elif args.images_only:
        await generate_images()
    else:
        await generate_audio()
        await generate_images()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
