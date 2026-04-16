"""
Analytics Service — Tracks user events in Firestore for measuring success metrics.

Events are written fire-and-forget to avoid blocking the main flow.
All data is anonymized (no PII stored).
"""

import asyncio
import hashlib
import logging
import time
from enum import Enum
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Analytics event types."""
    NARRATIVE_START = "narrative_start"
    NARRATIVE_COMPLETE = "narrative_complete"
    NARRATIVE_ABANDONED = "narrative_abandoned"
    NARRATIVE_ERROR = "narrative_error"
    FOLLOWUP_USED = "followup_used"
    LIVE_VOICE_STARTED = "live_voice_started"
    LIVE_VOICE_ENDED = "live_voice_ended"


# Firestore collection for analytics
_ANALYTICS_COLLECTION = "analytics"

# In-memory client (lazily initialized)
_firestore_client = None


def _get_client():
    """Get or create Firestore client."""
    global _firestore_client
    if _firestore_client is None:
        if not settings.USE_FIRESTORE:
            return None
        from google.cloud import firestore
        _firestore_client = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    return _firestore_client


def _hash_session_id(session_id: str) -> str:
    """Hash session ID for privacy (one-way, non-reversible)."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:16]


def _extract_region_key(region: str) -> str:
    """Normalize region string to a key for aggregation."""
    if not region:
        return "unknown"
    # Lowercase, take first word (e.g., "Ghana, West Africa" -> "ghana")
    return region.lower().split(",")[0].split()[0][:20]


async def track_event(
    event_type: EventType,
    session_id: str,
    region: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Track an analytics event (fire-and-forget).

    Args:
        event_type: The type of event
        session_id: Session ID (will be hashed)
        region: Region of origin (optional, for aggregation)
        metadata: Additional event metadata (optional)
    """
    if not settings.USE_FIRESTORE:
        logger.debug("[analytics] Skipped (Firestore disabled): %s", event_type.value)
        return

    try:
        # Run in background to avoid blocking
        asyncio.create_task(_write_event(event_type, session_id, region, metadata))
    except Exception as e:
        # Never let analytics errors affect the main flow
        logger.warning("[analytics] Failed to queue event: %s", e)


async def _write_event(
    event_type: EventType,
    session_id: str,
    region: Optional[str],
    metadata: Optional[dict],
) -> None:
    """Actually write the event to Firestore (runs in background)."""
    try:
        client = _get_client()
        if not client:
            return

        doc = {
            "event_type": event_type.value,
            "session_hash": _hash_session_id(session_id),
            "timestamp": time.time(),
            "region": _extract_region_key(region) if region else None,
        }

        if metadata:
            # Only include safe metadata fields
            safe_fields = {"segment_count", "duration_seconds", "error_type", "audio_enabled"}
            doc["metadata"] = {k: v for k, v in metadata.items() if k in safe_fields}

        # Write to Firestore (blocking, but we're in a background task)
        await asyncio.to_thread(
            lambda: client.collection(_ANALYTICS_COLLECTION).add(doc)
        )

        logger.debug("[analytics] Recorded: %s for session %s", event_type.value, doc["session_hash"])

    except Exception as e:
        logger.warning("[analytics] Write failed: %s", e)


async def get_aggregate_stats() -> dict:
    """
    Get aggregate statistics for the admin dashboard.

    Returns counts by event type and region distribution.
    """
    if not settings.USE_FIRESTORE:
        return {"error": "Analytics not available (Firestore disabled)"}

    try:
        client = _get_client()
        if not client:
            return {"error": "Firestore client not available"}

        collection = client.collection(_ANALYTICS_COLLECTION)

        # Get all events (limit to recent for performance)
        # In production, you'd use aggregation queries or pre-computed stats
        one_week_ago = time.time() - (7 * 24 * 60 * 60)

        events = await asyncio.to_thread(
            lambda: list(
                collection
                .where("timestamp", ">=", one_week_ago)
                .limit(10000)
                .stream()
            )
        )

        # Aggregate counts
        event_counts: dict[str, int] = {}
        region_counts: dict[str, int] = {}
        total_narratives = 0
        completed_narratives = 0

        for event_doc in events:
            data = event_doc.to_dict()
            event_type = data.get("event_type", "unknown")
            region = data.get("region", "unknown")

            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            if event_type == "narrative_start":
                total_narratives += 1
                if region:
                    region_counts[region] = region_counts.get(region, 0) + 1

            if event_type == "narrative_complete":
                completed_narratives += 1

        completion_rate = (
            round(completed_narratives / total_narratives * 100, 1)
            if total_narratives > 0 else 0
        )

        return {
            "period": "last_7_days",
            "event_counts": event_counts,
            "region_distribution": dict(sorted(region_counts.items(), key=lambda x: -x[1])[:10]),
            "total_narratives": total_narratives,
            "completed_narratives": completed_narratives,
            "completion_rate_percent": completion_rate,
        }

    except Exception as e:
        logger.error("[analytics] Stats query failed: %s", e, exc_info=True)
        return {"error": str(e)}
