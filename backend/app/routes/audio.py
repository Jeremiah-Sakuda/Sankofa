import logging
from fastapi import APIRouter, HTTPException
from app.services.tts_service import generate_narration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["audio"])


@router.post("/audio/generate")
async def generate_audio(request: dict):
    """Generate TTS audio for a text segment."""
    text = request.get("text", "")
    voice = request.get("voice", "Kore")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    audio_data = await generate_narration(text, voice)

    if not audio_data:
        raise HTTPException(status_code=500, detail="Audio generation failed")

    return {
        "audio_data": audio_data,
        "media_type": "audio/wav",
    }
