"""Share routes for public narrative sharing."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.models.user import User
from app.rate_limiter import limiter
from app.routes.auth import get_current_user
from app.store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["share"])


class ShareResponse(BaseModel):
    """Response for share endpoint."""
    share_url: str
    session_id: str


class PublicNarrativeResponse(BaseModel):
    """Response for public narrative view."""
    session_id: str
    family_name: str
    region: str
    era: str
    arc_title: str | None
    segments: list[dict]


@router.post("/narratives/{session_id}/share", response_model=ShareResponse)
@limiter.limit("10/minute")
async def share_narrative(
    request: Request,
    session_id: UUID,
    user: User = Depends(get_current_user),
):
    """Make a narrative publicly shareable.

    Sets is_public=True on the session. Anyone with the link can view it.
    User must own the narrative or the narrative must be unclaimed.
    """
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Check ownership - owned narratives require authentication
    if session.owner_id:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if session.owner_id != user.user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to share this narrative")

    # Make public
    session.is_public = True
    session_store.update_metadata(session)

    # Build share URL from configured frontend URL (prevents host header injection)
    share_url = f"{settings.FRONTEND_URL.rstrip('/')}/story/{session_id}"

    logger.info("Narrative %s shared by user %s", session_id, user.user_id if user else "anonymous")

    return ShareResponse(share_url=share_url, session_id=str(session_id))


@router.get("/story/{session_id}")
@limiter.limit("30/minute")
async def get_public_story(
    request: Request,
    session_id: UUID,
):
    """Get a publicly shared narrative for read-only viewing.

    Returns 404 if the narrative doesn't exist or isn't public.
    """
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Story not found")

    if not session.is_public:
        raise HTTPException(status_code=404, detail="Story not found")

    # Get arc title if available
    arc_title = None
    if session.arc_outline and isinstance(session.arc_outline, dict):
        arc_title = session.arc_outline.get("title")

    # Return public view - no audio data to reduce payload, images included
    segments = []
    for seg in session.segments:
        seg_dict = seg.model_dump()
        # Strip audio to reduce payload size - can be re-generated client-side if needed
        if seg.type == "audio":
            continue
        # Include images for visual experience
        segments.append(seg_dict)

    return {
        "session_id": str(session_id),
        "family_name": session.user_input.family_name,
        "region": session.user_input.region_of_origin,
        "era": session.user_input.time_period,
        "arc_title": arc_title,
        "arc_outline": session.arc_outline,
        "segments": segments,
    }


@router.delete("/narratives/{session_id}/share")
@limiter.limit("10/minute")
async def unshare_narrative(
    request: Request,
    session_id: UUID,
    user: User = Depends(get_current_user),
):
    """Remove public sharing from a narrative."""
    session = session_store.get(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Check ownership - owned narratives require authentication
    if session.owner_id:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if session.owner_id != user.user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to unshare this narrative")

    # Make private
    session.is_public = False
    session_store.update_metadata(session)

    logger.info("Narrative %s unshared by user %s", session_id, user.user_id if user else "anonymous")

    return {"message": "Narrative is now private"}
