"""
Generate TTS audio for all text segments in the sample narrative.

Usage:
    cd backend
    python ../scripts/generate_sample_tts.py

Requires GOOGLE_API_KEY in backend/.env or environment.
"""

import asyncio
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

from app.services.tts_service import generate_narration


async def main():
    sample_path = os.path.join(
        os.path.dirname(__file__),
        '..', 'backend', 'app', 'data', 'sample_narrative.json'
    )

    with open(sample_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data['segments']
    new_segments = []

    for seg in segments:
        new_segments.append(seg)

        # Generate TTS for text segments
        if seg['type'] == 'text' and seg.get('content'):
            print(f"Generating TTS for sequence {seg['sequence']} (Act {seg['act']})...")
            print(f"  Text preview: {seg['content'][:60]}...")

            result = await generate_narration(seg['content'])

            if result:
                audio_data, mime_type = result
                audio_seg = {
                    "type": "audio",
                    "content": seg['content'][:100],  # Preview
                    "media_data": audio_data,
                    "media_type": mime_type,
                    "trust_level": seg['trust_level'],
                    "sequence": seg['sequence'],
                    "act": seg['act'],
                    "is_hero": False
                }
                new_segments.append(audio_seg)
                print(f"  [OK] Generated {len(audio_data)} bytes of audio")
            else:
                print(f"  [FAIL] TTS generation failed")

    # Update segments
    data['segments'] = new_segments

    # Write back
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    text_count = len([s for s in new_segments if s['type'] == 'text'])
    audio_count = len([s for s in new_segments if s['type'] == 'audio'])
    image_count = len([s for s in new_segments if s['type'] == 'image'])

    print(f"\nDone! Sample narrative now has:")
    print(f"  {text_count} text segments")
    print(f"  {audio_count} audio segments")
    print(f"  {image_count} image segments")


if __name__ == '__main__':
    asyncio.run(main())
