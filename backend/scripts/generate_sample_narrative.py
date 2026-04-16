"""
Generate sample narrative with real Gemini images and TTS audio.

Run from backend directory:
    python scripts/generate_sample_narrative.py

This will update backend/app/data/sample_narrative.json with actual media data.
"""

import asyncio
import base64
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.genai.types import GenerateContentConfig, Modality
from app.services.gemini_service import get_client
from app.services.tts_service import generate_narration
from app.config import settings

SAMPLE_PATH = Path(__file__).parent.parent / "app" / "data" / "sample_narrative.json"

# Image prompts for each image segment (watercolor style)
IMAGE_PROMPTS = {
    0: """Watercolor illustration of the vast golden savanna of the Maasai Mara in Kenya,
stretching to the horizon with scattered acacia trees and distant purple mountains.
Warm earth tones of ochre, burnt sienna, and gold. Soft wet-on-wet edges, transparent
washes of pigment with white paper showing through. Hand-painted watercolor on textured
paper. 1940s East Africa, no people.""",

    3: """Watercolor illustration of a traditional Maasai enkang (homestead) with circular
thornbush fence enclosure, several dung-and-mud huts arranged inside, and cattle gathered
at dusk. Warm sunset light in burnt sienna and ochre tones. Visible brushstrokes, soft
edges, transparent washes. Hand-painted watercolor style. 1940s Kenya.""",

    6: """Watercolor illustration of Maasai warriors (morani) in red shuka cloths standing
tall with spears on the savanna at dawn, cattle grazing peacefully nearby. Warm golden
morning light, burnt sienna earth tones. Soft wet-on-wet watercolor technique, visible
brushstrokes, white paper showing through. 1940s East Africa.""",

    9: """Watercolor illustration of a Maasai elder teaching children under a spreading
acacia tree at sunset, with cattle silhouettes in the background. Warm golden and amber
tones, soft watercolor washes, visible brushstrokes. Hand-painted texture. 1940s Kenya
to present day, sense of continuity and tradition.""",
}


def generate_image_sync(prompt: str) -> tuple[str, str] | None:
    """Generate an image using Gemini's image model."""
    model = settings.GEMINI_IMAGE_MODEL or "gemini-2.0-flash-exp-image-generation"

    # Use image generation model
    try:
        client = get_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=[Modality.IMAGE],
                temperature=0.9,
            ),
        )

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                    mime_type = part.inline_data.mime_type or "image/png"
                    return image_b64, mime_type
    except Exception as e:
        print(f"    Image generation error: {e}")
        return None

    return None


async def generate_images(segments: list) -> list:
    """Generate images for image segments."""
    print("Generating images...")

    for seg in segments:
        if seg["type"] == "image" and seg["sequence"] in IMAGE_PROMPTS:
            prompt = IMAGE_PROMPTS[seg["sequence"]]
            print(f"  Generating image for sequence {seg['sequence']}...")

            try:
                result = await asyncio.to_thread(generate_image_sync, prompt)
                if result:
                    image_data, media_type = result
                    seg["media_data"] = image_data
                    seg["media_type"] = media_type
                    print(f"    [OK] Generated ({len(image_data) // 1024}KB)")
                else:
                    print(f"    [FAIL] Failed to generate")
            except Exception as e:
                print(f"    [ERROR] {e}")

    return segments


async def generate_audio(segments: list) -> list:
    """Generate TTS audio for text segments."""
    print("Generating TTS audio...")

    audio_segments = []

    for seg in segments:
        if seg["type"] == "text" and seg.get("content"):
            print(f"  Generating audio for sequence {seg['sequence']}...")

            try:
                result = await generate_narration(seg["content"])
                if result:
                    audio_data, media_type = result
                    # Create audio segment
                    audio_seg = {
                        "type": "audio",
                        "content": seg["content"][:100],
                        "media_data": audio_data,
                        "media_type": media_type,
                        "trust_level": seg["trust_level"],
                        "sequence": seg["sequence"],
                        "act": seg.get("act"),
                        "is_hero": False,
                    }
                    audio_segments.append(audio_seg)
                    print(f"    [OK] Generated ({len(audio_data) // 1024}KB)")
                else:
                    print(f"    [FAIL] No audio returned")
            except Exception as e:
                print(f"    [ERROR] {e}")

    return audio_segments


async def main():
    print(f"Loading sample narrative from {SAMPLE_PATH}")

    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        sample = json.load(f)

    segments = sample["segments"]

    # Generate images
    segments = await generate_images(segments)

    # Generate audio
    audio_segments = await generate_audio(segments)

    # Combine - add audio segments after their corresponding text segments
    all_segments = []
    audio_by_seq = {a["sequence"]: a for a in audio_segments}

    for seg in segments:
        all_segments.append(seg)
        # Add audio right after its text segment
        if seg["sequence"] in audio_by_seq:
            all_segments.append(audio_by_seq[seg["sequence"]])

    sample["segments"] = all_segments

    # Save
    print(f"\nSaving to {SAMPLE_PATH}")
    with open(SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)

    # Stats
    image_count = sum(1 for s in all_segments if s["type"] == "image" and s.get("media_data"))
    audio_count = sum(1 for s in all_segments if s["type"] == "audio" and s.get("media_data"))
    total_size = sum(len(s.get("media_data", "") or "") for s in all_segments)

    print(f"\n[DONE]")
    print(f"  Images: {image_count}")
    print(f"  Audio:  {audio_count}")
    print(f"  Total size: {total_size // 1024}KB")


if __name__ == "__main__":
    asyncio.run(main())
