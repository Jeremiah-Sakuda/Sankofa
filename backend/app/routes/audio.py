import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import AudioGenerateRequest
from app.services.tts_service import generate_narration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["audio"])


@router.post("/audio/generate")
async def generate_audio(request: AudioGenerateRequest):
    """Generate TTS audio for a text segment."""
    audio_data = await generate_narration(request.text, request.voice)

    if not audio_data:
        raise HTTPException(status_code=500, detail="Audio generation failed")

    return {
        "audio_data": audio_data,
        "media_type": "audio/wav",
    }
