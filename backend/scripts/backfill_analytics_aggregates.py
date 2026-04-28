#!/usr/bin/env python3
"""
Backfill analytics aggregate documents from historical events.

This script rebuilds daily aggregate documents from existing analytics events
for the past N days (default: 30).

Usage:
    python scripts/backfill_analytics_aggregates.py [--dry-run] [--days N]

Options:
    --dry-run   Preview changes without writing to Firestore
    --days N    Number of days to backfill (default: 30)
"""

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore

from app.config import settings
from app.store.firestore_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_ANALYTICS_COLLECTION = "analytics"
_AGGREGATES_COLLECTION = "analytics_aggregates"


def backfill_analytics_aggregates(dry_run: bool = False, days: int = 30) -> dict:
    """
    Rebuild daily aggregate documents from historical events.

    For each day:
    1. Query all events from that day
    2. Aggregate event counts, region counts, and narrative totals
    3. Write to analytics_aggregates/daily/{YYYY-MM-DD}

    Returns:
        dict with statistics about the backfill operation
    """
    if not settings.USE_FIRESTORE:
        logger.error("Firestore is not enabled. Set USE_FIRESTORE=true.")
        return {"error": "Firestore not enabled"}

    client = get_client()
    analytics_collection = client.collection(_ANALYTICS_COLLECTION)
    aggregates_collection = client.collection(_AGGREGATES_COLLECTION)

    stats = {
        "days_processed": 0,
        "events_processed": 0,
        "aggregates_written": 0,
        "errors": 0,
    }

    # Process each day
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for day_offset in range(days):
        day_start = today - timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)
        date_str = day_start.strftime("%Y-%m-%d")

        try:
            # Query events for this day
            events = list(
                analytics_collection
                .where("timestamp", ">=", day_start.timestamp())
                .where("timestamp", "<", day_end.timestamp())
                .stream()
            )

            if not events:
                logger.debug("No events for %s", date_str)
                continue

            # Aggregate counts
            event_counts: dict[str, int] = defaultdict(int)
            region_counts: dict[str, int] = defaultdict(int)
            total_narratives = 0
            completed_narratives = 0

            for event_doc in events:
                data = event_doc.to_dict()
                event_type = data.get("event_type", "unknown")
                region = data.get("region")

                event_counts[event_type] += 1
                stats["events_processed"] += 1

                if event_type == "narrative_start":
                    total_narratives += 1
                    if region:
                        region_counts[region] += 1
                elif event_type == "narrative_complete":
                    completed_narratives += 1

            # Build aggregate document
            aggregate_doc = {
                "date": date_str,
                "event_counts": dict(event_counts),
                "region_counts": dict(region_counts),
                "total_narratives": total_narratives,
                "completed_narratives": completed_narratives,
            }

            if dry_run:
                logger.info("[DRY RUN] Would write aggregate for %s: %d events, %d narratives",
                           date_str, len(events), total_narratives)
            else:
                aggregates_collection.document(f"daily/{date_str}").set(aggregate_doc)
                logger.info("Wrote aggregate for %s: %d events, %d narratives",
                           date_str, len(events), total_narratives)

            stats["days_processed"] += 1
            stats["aggregates_written"] += 1

        except Exception as e:
            logger.error("Error processing day %s: %s", date_str, e)
            stats["errors"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill analytics aggregates from historical events")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backfill")
    args = parser.parse_args()

    logger.info("Starting analytics aggregates backfill (dry_run=%s, days=%d)",
               args.dry_run, args.days)

    stats = backfill_analytics_aggregates(dry_run=args.dry_run, days=args.days)

    logger.info("Backfill complete: %s", stats)
    print(f"\nResults:\n"
          f"  Days processed: {stats.get('days_processed', 0)}\n"
          f"  Events processed: {stats.get('events_processed', 0)}\n"
          f"  Aggregates written: {stats.get('aggregates_written', 0)}\n"
          f"  Errors: {stats.get('errors', 0)}")


if __name__ == "__main__":
    main()
