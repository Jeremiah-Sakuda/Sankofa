#!/usr/bin/env python3
"""
Backfill contribution aggregate documents from historical contributions.

This script rebuilds daily aggregate documents and all-time totals from
existing contribution records.

Usage:
    python scripts/backfill_contributions_aggregates.py [--dry-run] [--days N]

Options:
    --dry-run   Preview changes without writing to Firestore
    --days N    Number of days to backfill (default: 90)
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

_CONTRIBUTIONS_COLLECTION = "contributions"
_AGGREGATES_COLLECTION = "contributions_aggregates"


def backfill_contributions_aggregates(dry_run: bool = False, days: int = 90) -> dict:
    """
    Rebuild daily aggregate documents and all-time totals from historical contributions.

    For each day:
    1. Query all completed contributions from that day
    2. Aggregate contribution counts and amounts
    3. Write to contributions_aggregates/daily/{YYYY-MM-DD}

    Also writes all-time totals to contributions_aggregates/totals/all_time

    Returns:
        dict with statistics about the backfill operation
    """
    if not settings.USE_FIRESTORE:
        logger.error("Firestore is not enabled. Set USE_FIRESTORE=true.")
        return {"error": "Firestore not enabled"}

    client = get_client()
    contributions_collection = client.collection(_CONTRIBUTIONS_COLLECTION)
    aggregates_collection = client.collection(_AGGREGATES_COLLECTION)

    stats = {
        "days_processed": 0,
        "contributions_processed": 0,
        "aggregates_written": 0,
        "errors": 0,
    }

    # Track all-time totals
    all_time_contributions = 0
    all_time_amount = 0

    # Process each day
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for day_offset in range(days):
        day_start = today - timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)
        date_str = day_start.strftime("%Y-%m-%d")

        try:
            # Query completed contributions for this day
            contributions = list(
                contributions_collection
                .where("status", "==", "completed")
                .where("created_at", ">=", day_start.timestamp())
                .where("created_at", "<", day_end.timestamp())
                .stream()
            )

            if not contributions:
                logger.debug("No contributions for %s", date_str)
                continue

            # Aggregate counts
            total_contributions = 0
            total_amount = 0
            count_by_amount: dict[int, int] = defaultdict(int)

            for contrib_doc in contributions:
                data = contrib_doc.to_dict()
                amount = data.get("amount_cents", 0)

                total_contributions += 1
                total_amount += amount
                count_by_amount[amount] += 1
                stats["contributions_processed"] += 1

            # Update all-time totals
            all_time_contributions += total_contributions
            all_time_amount += total_amount

            # Build aggregate document
            aggregate_doc = {
                "date": date_str,
                "total_contributions": total_contributions,
                "total_amount_cents": total_amount,
                "count_by_amount": {str(k): v for k, v in count_by_amount.items()},
            }

            if dry_run:
                logger.info("[DRY RUN] Would write aggregate for %s: %d contributions, $%.2f",
                           date_str, total_contributions, total_amount / 100)
            else:
                aggregates_collection.document(f"daily/{date_str}").set(aggregate_doc)
                logger.info("Wrote aggregate for %s: %d contributions, $%.2f",
                           date_str, total_contributions, total_amount / 100)

            stats["days_processed"] += 1
            stats["aggregates_written"] += 1

        except Exception as e:
            logger.error("Error processing day %s: %s", date_str, e)
            stats["errors"] += 1

    # Write all-time totals
    if all_time_contributions > 0:
        all_time_doc = {
            "total_contributions": all_time_contributions,
            "total_amount_cents": all_time_amount,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        if dry_run:
            logger.info("[DRY RUN] Would write all-time totals: %d contributions, $%.2f",
                       all_time_contributions, all_time_amount / 100)
        else:
            aggregates_collection.document("totals/all_time").set(all_time_doc)
            logger.info("Wrote all-time totals: %d contributions, $%.2f",
                       all_time_contributions, all_time_amount / 100)
            stats["aggregates_written"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill contribution aggregates from historical data")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--days", type=int, default=90, help="Number of days to backfill")
    args = parser.parse_args()

    logger.info("Starting contribution aggregates backfill (dry_run=%s, days=%d)",
               args.dry_run, args.days)

    stats = backfill_contributions_aggregates(dry_run=args.dry_run, days=args.days)

    logger.info("Backfill complete: %s", stats)
    print(f"\nResults:\n"
          f"  Days processed: {stats.get('days_processed', 0)}\n"
          f"  Contributions processed: {stats.get('contributions_processed', 0)}\n"
          f"  Aggregates written: {stats.get('aggregates_written', 0)}\n"
          f"  Errors: {stats.get('errors', 0)}")


if __name__ == "__main__":
    main()
