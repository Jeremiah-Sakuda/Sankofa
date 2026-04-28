#!/usr/bin/env python3
"""
Backfill denormalized session metadata for existing sessions.

This script adds segment_count, first_image_data, and first_image_type
to existing session documents that were created before the N+1 optimization.

Usage:
    python scripts/backfill_session_metadata.py [--dry-run] [--batch-size N]

Options:
    --dry-run       Preview changes without writing to Firestore
    --batch-size N  Number of sessions to process per batch (default: 100)
"""

import argparse
import logging
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore

from app.config import settings
from app.store.firestore_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def backfill_session_metadata(dry_run: bool = False, batch_size: int = 100) -> dict:
    """
    Backfill denormalized metadata for all sessions.

    For each session:
    1. Read segments subcollection
    2. Calculate segment_count
    3. Find first image segment for thumbnail
    4. Update session doc with denormalized fields

    Returns:
        dict with statistics about the backfill operation
    """
    if not settings.USE_FIRESTORE:
        logger.error("Firestore is not enabled. Set USE_FIRESTORE=true.")
        return {"error": "Firestore not enabled"}

    client = get_client()
    sessions_collection = client.collection(settings.FIRESTORE_SESSIONS_COLLECTION)

    stats = {
        "total_sessions": 0,
        "updated_sessions": 0,
        "skipped_sessions": 0,
        "errors": 0,
    }

    # Process sessions in batches
    last_doc = None
    while True:
        query = sessions_collection.order_by("created_at").limit(batch_size)
        if last_doc:
            query = query.start_after(last_doc)

        docs = list(query.stream())
        if not docs:
            break

        for doc in docs:
            stats["total_sessions"] += 1
            session_id = doc.id
            data = doc.to_dict()

            # Skip if already has denormalized fields
            if data.get("segment_count") is not None:
                logger.debug("Skipping %s: already has segment_count", session_id)
                stats["skipped_sessions"] += 1
                continue

            try:
                # Read segments subcollection
                seg_docs = list(doc.reference.collection("segments").stream())
                segment_count = len(seg_docs)

                # Find first image for thumbnail
                first_image_data = None
                first_image_type = None
                for seg_doc in sorted(seg_docs, key=lambda d: d.to_dict().get("sequence", 0)):
                    seg_data = seg_doc.to_dict()
                    if seg_data.get("type") == "image" and seg_data.get("media_data"):
                        first_image_data = seg_data["media_data"]
                        first_image_type = seg_data.get("media_type")
                        break

                # Prepare update
                updates = {
                    "segment_count": segment_count,
                    "first_image_data": first_image_data,
                    "first_image_type": first_image_type,
                }

                if dry_run:
                    logger.info("[DRY RUN] Would update %s: segment_count=%d, has_image=%s",
                               session_id, segment_count, first_image_data is not None)
                else:
                    doc.reference.update(updates)
                    logger.info("Updated %s: segment_count=%d, has_image=%s",
                               session_id, segment_count, first_image_data is not None)

                stats["updated_sessions"] += 1

            except Exception as e:
                logger.error("Error processing session %s: %s", session_id, e)
                stats["errors"] += 1

        last_doc = docs[-1]
        logger.info("Processed batch of %d sessions (total: %d)", len(docs), stats["total_sessions"])

    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill session metadata for N+1 optimization")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--batch-size", type=int, default=100, help="Sessions per batch")
    args = parser.parse_args()

    logger.info("Starting session metadata backfill (dry_run=%s, batch_size=%d)",
               args.dry_run, args.batch_size)

    stats = backfill_session_metadata(dry_run=args.dry_run, batch_size=args.batch_size)

    logger.info("Backfill complete: %s", stats)
    print(f"\nResults:\n"
          f"  Total sessions: {stats.get('total_sessions', 0)}\n"
          f"  Updated: {stats.get('updated_sessions', 0)}\n"
          f"  Skipped (already had metadata): {stats.get('skipped_sessions', 0)}\n"
          f"  Errors: {stats.get('errors', 0)}")


if __name__ == "__main__":
    main()
