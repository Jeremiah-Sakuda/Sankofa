"""
Analytics Service — Tracks user events in Firestore for measuring success metrics.

Events are written fire-and-forget to avoid blocking the main flow.
All data is anonymized (no PII stored).

Aggregation Strategy:
- Each event write also updates a daily aggregate document
- get_aggregate_stats() reads 7 daily docs instead of scanning 10k events
- Daily docs stored in: analytics_aggregates/daily/{YYYY-MM-DD}
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
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
    # Contribution (tip jar) events
    TIP_CARD_SHOWN = "tip_card_shown"
    TIP_CARD_DISMISSED = "tip_card_dismissed"
    TIP_AMOUNT_SELECTED = "tip_amount_selected"
    TIP_CHECKOUT_STARTED = "tip_checkout_started"
    TIP_COMPLETED = "tip_completed"


# Firestore collections for analytics
_ANALYTICS_COLLECTION = "analytics"
_ANALYTICS_AGGREGATES_COLLECTION = "analytics_aggregates"


def _get_client():
    """Get the shared Firestore client."""
    if not settings.USE_FIRESTORE:
        return None
    from app.store.firestore_client import get_client
    return get_client()


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
    """Actually write the event to Firestore (runs in background).

    Also updates daily aggregate document for efficient stats queries.
    """
    try:
        client = _get_client()
        if not client:
            return

        region_key = _extract_region_key(region) if region else None

        doc = {
            "event_type": event_type.value,
            "session_hash": _hash_session_id(session_id),
            "timestamp": time.time(),
            "region": region_key,
        }

        if metadata:
            # Only include safe metadata fields
            safe_fields = {"segment_count", "duration_seconds", "error_type", "audio_enabled", "amount_cents"}
            doc["metadata"] = {k: v for k, v in metadata.items() if k in safe_fields}

        # Write event and update aggregate in parallel
        await asyncio.gather(
            asyncio.to_thread(lambda: client.collection(_ANALYTICS_COLLECTION).add(doc)),
            _update_analytics_aggregate(client, event_type, region_key),
        )

        logger.debug("[analytics] Recorded: %s for session %s", event_type.value, doc["session_hash"])

    except Exception as e:
        logger.warning("[analytics] Write failed: %s", e)


async def _update_analytics_aggregate(
    client,
    event_type: EventType,
    region: Optional[str],
) -> None:
    """Update daily aggregate document with event counts.

    Document structure: analytics_aggregates/daily/{YYYY-MM-DD}
    {
        "date": "2024-01-15",
        "event_counts": {"narrative_start": 10, "narrative_complete": 8, ...},
        "region_counts": {"ghana": 5, "nigeria": 3, ...},
        "total_narratives": 10,
        "completed_narratives": 8
    }
    """
    try:
        from google.cloud import firestore as fs

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        doc_ref = client.collection(_ANALYTICS_AGGREGATES_COLLECTION).document(f"daily/{today}")

        # Build update dict
        updates = {
            "date": today,
            f"event_counts.{event_type.value}": fs.Increment(1),
        }

        # Track narrative counts for easy completion rate calculation
        if event_type == EventType.NARRATIVE_START:
            updates["total_narratives"] = fs.Increment(1)
            if region:
                updates[f"region_counts.{region}"] = fs.Increment(1)
        elif event_type == EventType.NARRATIVE_COMPLETE:
            updates["completed_narratives"] = fs.Increment(1)

        await asyncio.to_thread(lambda: doc_ref.set(updates, merge=True))

    except Exception as e:
        # Don't let aggregate errors affect the main event write
        logger.warning("[analytics] Aggregate update failed: %s", e)


async def get_aggregate_stats() -> dict:
    """
    Get aggregate statistics for the admin dashboard.

    Reads from pre-computed daily aggregate documents instead of scanning
    all events. This reduces Firestore reads from ~10,000 to 7.

    Returns counts by event type and region distribution.
    """
    if not settings.USE_FIRESTORE:
        return {"error": "Analytics not available (Firestore disabled)"}

    try:
        client = _get_client()
        if not client:
            return {"error": "Firestore client not available"}

        # Generate date strings for the last 7 days
        today = datetime.now(timezone.utc)
        date_strings = [
            (today - __import__("datetime").timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
        ]

        # Read all 7 daily aggregate docs
        def fetch_daily_docs():
            docs = []
            for date_str in date_strings:
                doc_ref = client.collection(_ANALYTICS_AGGREGATES_COLLECTION).document(f"daily/{date_str}")
                doc = doc_ref.get()
                if doc.exists:
                    docs.append(doc.to_dict())
            return docs

        daily_docs = await asyncio.to_thread(fetch_daily_docs)

        # Aggregate across days
        event_counts: dict[str, int] = {}
        region_counts: dict[str, int] = {}
        total_narratives = 0
        completed_narratives = 0

        for doc_data in daily_docs:
            # Merge event counts
            for event_type, count in doc_data.get("event_counts", {}).items():
                event_counts[event_type] = event_counts.get(event_type, 0) + count

            # Merge region counts
            for region, count in doc_data.get("region_counts", {}).items():
                region_counts[region] = region_counts.get(region, 0) + count

            # Sum narrative totals
            total_narratives += doc_data.get("total_narratives", 0)
            completed_narratives += doc_data.get("completed_narratives", 0)

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
        return {"error": "Failed to retrieve analytics data"}
