import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import AudioGenerateRequest
from app.rate_limiter import limiter
from app.services.tts_service import generate_narration

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["audio"])


@router.post("/audio/generate")
@limiter.limit("30/minute")
async def generate_audio(request: Request, payload: AudioGenerateRequest):
    """Generate TTS audio for a text segment."""
    result = await generate_narration(payload.text, payload.voice)

    if not result:
        raise HTTPException(status_code=500, detail="Audio generation failed")

    b64_data, mime_type = result
    return {
        "audio_data": b64_data,
        "media_type": mime_type,
    }
