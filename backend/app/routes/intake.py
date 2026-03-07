import uuid
from fastapi import APIRouter, HTTPException
from app.models.schemas import UserInput, IntakeResponse
from app.models.session import session_store

router = APIRouter(prefix="/api", tags=["intake"])


@router.post("/intake", response_model=IntakeResponse)
async def create_session(user_input: UserInput):
    session_id = str(uuid.uuid4())
    session_store.create(session_id, user_input)
    return IntakeResponse(
        session_id=session_id,
        message=f"Session created. Ready to generate narrative for the {user_input.family_name} family heritage.",
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "user_input": session.user_input.model_dump(),
        "segment_count": len(session.segments),
        "is_generating": session.is_generating,
    }
