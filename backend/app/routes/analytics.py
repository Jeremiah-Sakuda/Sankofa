"""Analytics routes for frontend event tracking."""

import logging
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.rate_limiter import limiter
from app.services.analytics import EventType, track_event
from app.store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class TrackEventRequest(BaseModel):
    """Request to track an analytics event from frontend."""
    event_type: str
    session_id: str
    metadata: Optional[dict] = None


# Allowed frontend event types (subset of EventType for security)
_ALLOWED_FRONTEND_EVENTS = {
    "tip_card_shown",
    "tip_card_dismissed",
    "tip_amount_selected",
}


@router.post("/track")
@limiter.limit("30/minute")
async def track_frontend_event(request: Request, body: TrackEventRequest):
    """
    Track an analytics event from the frontend.

    Only allows specific event types for security (prevents injection of fake events).
    Fire-and-forget - always returns success to avoid blocking UI.
    """
    # Validate event type
    if body.event_type not in _ALLOWED_FRONTEND_EVENTS:
        # Silently ignore invalid events (don't expose valid event names)
        return {"received": True}

    # Get region from session if available
    region = None
    session = session_store.get(body.session_id)
    if session and session.user_input:
        region = session.user_input.region_of_origin

    # Map string to EventType enum
    try:
        event_type = EventType(body.event_type)
    except ValueError:
        return {"received": True}

    # Track the event
    await track_event(
        event_type=event_type,
        session_id=body.session_id,
        region=region,
        metadata=body.metadata,
    )

    return {"received": True}
