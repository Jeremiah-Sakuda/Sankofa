import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import IntakeResponse, UserInput
from app.rate_limiter import limiter
from app.store import session_store
from app.utils.sanitization import is_suspicious_input, sanitize_user_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["intake"])


@router.post("/intake", response_model=IntakeResponse)
@limiter.limit("5/minute")
async def create_session(request: Request, user_input: UserInput):
    # Sanitize all user inputs to prevent prompt injection
    sanitized_input = sanitize_user_input(user_input)

    # Log suspicious inputs for monitoring (but still allow them after sanitization)
    for field_name in ["family_name", "region_of_origin", "time_period", "known_fragments"]:
        original_value = getattr(user_input, field_name, None)
        if original_value and is_suspicious_input(original_value):
            logger.warning(f"[intake] Suspicious input detected in {field_name}")

    session_id = str(uuid.uuid4())
    session_store.create(session_id, sanitized_input)
    return IntakeResponse(
        session_id=session_id,
        message=f"Session created. Ready to generate narrative for the {sanitized_input.family_name} family heritage.",
    )


@router.get("/session/{session_id}")
@limiter.limit("20/minute")
async def get_session(request: Request, session_id: UUID):
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "user_input": session.user_input.model_dump(),
        "segment_count": len(session.segments),
        "is_generating": session.is_generating,
    }
