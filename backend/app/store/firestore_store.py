"""Firestore-backed session store. Sessions in main collection; segments in subcollection to stay under 1 MiB doc limit."""

import logging
import time
from typing import Optional

from google.cloud import firestore

from app.config import settings
from app.models.schemas import NarrativeSegment, UserInput
from app.models.session import Session
from app.store.firestore_client import get_client

logger = logging.getLogger(__name__)

# Session TTL in seconds (24 hours)
_SESSION_TTL_SECONDS = 24 * 60 * 60


def _session_to_doc(session: Session, include_ttl: bool = False) -> dict:
    """Session document fields (no segments; those go in subcollection).

    Includes denormalized segment metadata for efficient list_by_owner queries:
    - segment_count: Number of segments (avoids subcollection read)
    - first_image_data: Base64 data of first image segment (for thumbnail)
    - first_image_type: MIME type of first image segment
    """
    # Find first image segment for thumbnail
    first_image = next(
        (s for s in session.segments if s.type == "image" and s.media_data),
        None
    )

    doc = {
        "user_input": session.user_input.model_dump(),
        "narrative_context": session.narrative_context,
        "is_generating": session.is_generating,
        "generating_started_at": session.generating_started_at,
        "arc_outline": session.arc_outline,
        "created_at": session.created_at,
        "owner_id": getattr(session, "owner_id", None),
        "is_public": getattr(session, "is_public", False),
        # Denormalized segment metadata
        "segment_count": len(session.segments),
        "first_image_data": first_image.media_data if first_image else None,
        "first_image_type": first_image.media_type if first_image else None,
    }
    if include_ttl:
        doc["expires_at"] = session.created_at + _SESSION_TTL_SECONDS
    return doc


def _doc_to_session(session_id: str, data: dict, segments: list[NarrativeSegment]) -> Session:
    return Session(
        session_id=session_id,
        user_input=UserInput.model_validate(data["user_input"]),
        segments=segments,
        narrative_context=data.get("narrative_context") or "",
        is_generating=data.get("is_generating") or False,
        generating_started_at=data.get("generating_started_at") or 0.0,
        arc_outline=data.get("arc_outline"),
        created_at=data.get("created_at") or time.time(),
        owner_id=data.get("owner_id"),
        is_public=data.get("is_public") or False,
    )


class FirestoreSessionStore:
    """Session store backed by Firestore. Main doc per session; segments in subcollection."""

    def __init__(self):
        self._client: Optional[firestore.Client] = None
        self._collection_name = settings.FIRESTORE_SESSIONS_COLLECTION

    def _client_or_init(self) -> firestore.Client:
        if self._client is None:
            self._client = get_client()
        return self._client

    def create(self, session_id: str, user_input: UserInput) -> Session:
        try:
            session = Session(session_id=session_id, user_input=user_input)
            doc_ref = self._client_or_init().collection(self._collection_name).document(session_id)
            doc_ref.set(_session_to_doc(session, include_ttl=True))
            logger.info("Firestore: created session %s (TTL: %d hours)", session_id, _SESSION_TTL_SECONDS // 3600)
            return session
        except Exception as e:
            logger.error("Firestore create error: %s", e, exc_info=True)
            raise RuntimeError("Failed to create session in data store.") from e

    def get(self, session_id: str) -> Optional[Session]:
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            if not data:
                return None
            # Load segments subcollection (ordered by doc id = sequence)
            seg_refs = doc_ref.collection("segments").order_by("sequence").stream()
            segments = []
            for seg_doc in seg_refs:
                seg_data = seg_doc.to_dict()
                if seg_data:
                    segments.append(NarrativeSegment.model_validate(seg_data))
            return _doc_to_session(session_id, data, segments)
        except Exception as e:
            logger.error("Firestore get error: %s", e, exc_info=True)
            raise RuntimeError("Failed to retrieve session from data store.") from e

    def update(self, session: Session) -> None:
        """Update the entire session including segments. Prefer update_metadata + append_segment for streaming."""
        try:
            client = self._client_or_init()
            doc_ref = client.collection(self._collection_name).document(session.session_id)
            seg_coll = doc_ref.collection("segments")

            # Use a batch to atomically delete old segments and add new ones
            batch = client.batch()
            batch.update(doc_ref, _session_to_doc(session))

            # Delete existing segments
            for seg_doc in seg_coll.stream():
                batch.delete(seg_doc.reference)

            # Add new segments
            for seg in session.segments:
                seg_dict = seg.model_dump()
                # Strip media_data that exceeds Firestore's 1 MiB field limit.
                # Audio/image blobs are already streamed to the client via SSE,
                # so Firestore only needs the metadata for session recovery.
                if seg_dict.get("media_data") and len(seg_dict["media_data"]) > 900_000:
                    seg_dict["media_data"] = None
                batch.set(seg_coll.document(str(seg.sequence)), seg_dict)

            batch.commit()
            logger.debug("Firestore: updated session %s (%d segments)", session.session_id, len(session.segments))
        except Exception as e:
            logger.error("Firestore update error: %s", e, exc_info=True)
            raise RuntimeError("Failed to update session in data store.") from e

    def update_metadata(self, session: Session) -> None:
        """Update only session metadata (not segments). O(1) operation.

        Use this instead of update() during streaming to avoid bulk segment rewrites.
        """
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session.session_id)
            doc_ref.set(_session_to_doc(session), merge=True)
            logger.debug("Firestore: updated metadata for session %s", session.session_id)
        except Exception as e:
            logger.error("Firestore update_metadata error: %s", e, exc_info=True)
            raise RuntimeError("Failed to update session metadata in data store.") from e

    def append_segment(self, session_id: str, segment: NarrativeSegment) -> None:
        """Append a single segment to the subcollection. O(1) operation.

        Use this instead of update() during streaming to avoid bulk segment rewrites.
        Also atomically updates denormalized metadata (segment_count, first_image).
        """
        try:
            client = self._client_or_init()
            doc_ref = client.collection(self._collection_name).document(session_id)
            seg_coll = doc_ref.collection("segments")
            seg_dict = segment.model_dump()

            # Strip media_data that exceeds Firestore's 1 MiB field limit.
            media_data = seg_dict.get("media_data")
            if media_data and len(media_data) > 900_000:
                seg_dict["media_data"] = None
                media_data = None  # Don't use for first_image either

            # Use batch for atomic update of segment + denormalized fields
            batch = client.batch()

            # Add segment to subcollection
            batch.set(seg_coll.document(str(segment.sequence)), seg_dict)

            # Update denormalized metadata on session doc
            update_fields = {
                "segment_count": firestore.Increment(1),
            }

            # Set first_image fields if this is the first image segment
            # Only set if first_image_data is not already set (use update with conditional)
            if segment.type == "image" and media_data:
                # We need to check if first_image_data is already set
                # Use a transaction for this conditional update
                @firestore.transactional
                def update_first_image(transaction, doc_ref, segment):
                    doc = doc_ref.get(transaction=transaction)
                    data = doc.to_dict() if doc.exists else {}

                    updates = {"segment_count": firestore.Increment(1)}
                    if not data.get("first_image_data"):
                        updates["first_image_data"] = segment.media_data
                        updates["first_image_type"] = segment.media_type

                    transaction.update(doc_ref, updates)

                transaction = client.transaction()
                update_first_image(transaction, doc_ref, segment)
                # Commit the segment separately since transaction handles the doc
                seg_coll.document(str(segment.sequence)).set(seg_dict)
            else:
                # Simple batch update for non-image segments
                batch.update(doc_ref, update_fields)
                batch.commit()

            logger.debug("Firestore: appended segment %d to session %s", segment.sequence, session_id)
        except Exception as e:
            logger.error("Firestore append_segment error: %s", e, exc_info=True)
            raise RuntimeError("Failed to append segment to data store.") from e

    def exists(self, session_id: str) -> bool:
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session_id)
            return doc_ref.get().exists
        except Exception as e:
            logger.error("Firestore exists error: %s", e, exc_info=True)
            raise RuntimeError("Failed to verify session existence in data store.") from e

    def list_by_owner(self, owner_id: str, limit: int = 50) -> list[Session]:
        """List sessions owned by a user, sorted by created_at descending."""
        try:
            collection = self._client_or_init().collection(self._collection_name)
            query = (
                collection
                .where(filter=firestore.FieldFilter("owner_id", "==", owner_id))
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            sessions = []
            for doc in query.stream():
                data = doc.to_dict()
                if not data:
                    continue
                # Load segments for each session
                seg_refs = doc.reference.collection("segments").order_by("sequence").stream()
                segments = []
                for seg_doc in seg_refs:
                    seg_data = seg_doc.to_dict()
                    if seg_data:
                        segments.append(NarrativeSegment.model_validate(seg_data))
                sessions.append(_doc_to_session(doc.id, data, segments))

            logger.debug("Firestore: listed %d sessions for owner %s", len(sessions), owner_id)
            return sessions
        except Exception as e:
            logger.error("Firestore list_by_owner error: %s", e, exc_info=True)
            return []

    def list_by_owner_summary(self, owner_id: str, limit: int = 50) -> list[dict]:
        """List session summaries owned by a user, sorted by created_at descending.

        Returns dict summaries with denormalized fields - no segment subcollection reads.
        This is O(1) read instead of O(N+1) where N is the number of sessions.

        Returns list of dicts with keys:
            session_id, family_name, region, era, created_at, segment_count,
            first_image_data, first_image_type, arc_title
        """
        try:
            collection = self._client_or_init().collection(self._collection_name)
            query = (
                collection
                .where(filter=firestore.FieldFilter("owner_id", "==", owner_id))
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            summaries = []
            for doc in query.stream():
                data = doc.to_dict()
                if not data:
                    continue

                user_input = data.get("user_input", {})
                arc_outline = data.get("arc_outline")

                summaries.append({
                    "session_id": doc.id,
                    "family_name": user_input.get("family_name", ""),
                    "region": user_input.get("region_of_origin", ""),
                    "era": user_input.get("time_period", ""),
                    "created_at": data.get("created_at", 0),
                    "segment_count": data.get("segment_count", 0),
                    "first_image_data": data.get("first_image_data"),
                    "first_image_type": data.get("first_image_type"),
                    "arc_title": arc_outline.get("title") if isinstance(arc_outline, dict) else None,
                })

            logger.debug("Firestore: listed %d session summaries for owner %s", len(summaries), owner_id)
            return summaries
        except Exception as e:
            logger.error("Firestore list_by_owner_summary error: %s", e, exc_info=True)
            return []

    def set_owner(self, session_id: str, owner_id: str) -> bool:
        """Set the owner of a session. Returns True on success."""
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session_id)
            doc_ref.update({"owner_id": owner_id})
            logger.info("Firestore: set owner %s for session %s", owner_id, session_id)
            return True
        except Exception as e:
            logger.error("Firestore set_owner error: %s", e, exc_info=True)
            return False

    def cleanup_expired(self, batch_size: int = 50) -> int:
        """Delete expired sessions and their segments using batch writes.

        Uses batch deletes for efficiency (up to 500 operations per batch,
        which is Firestore's limit).

        Args:
            batch_size: Maximum number of sessions to delete in one call

        Returns:
            Number of sessions deleted
        """
        # Firestore batch limit is 500 operations
        _BATCH_LIMIT = 500

        try:
            now = time.time()
            client = self._client_or_init()
            collection = client.collection(self._collection_name)

            # Query for expired sessions
            expired_query = (
                collection
                .where(filter=firestore.FieldFilter("expires_at", "<", now))
                .limit(batch_size)
            )

            # Collect all delete operations
            delete_ops: list[tuple[str, firestore.DocumentReference]] = []  # (type, ref)

            for doc in expired_query.stream():
                session_id = doc.id
                doc_ref = collection.document(session_id)

                # Collect segment deletes
                seg_coll = doc_ref.collection("segments")
                for seg_doc in seg_coll.stream():
                    delete_ops.append(("segment", seg_doc.reference))

                # Collect session doc delete (after its segments)
                delete_ops.append(("session", doc_ref))

            if not delete_ops:
                return 0

            # Execute deletes in batches of 500
            deleted_sessions = 0
            for i in range(0, len(delete_ops), _BATCH_LIMIT):
                batch = client.batch()
                batch_ops = delete_ops[i:i + _BATCH_LIMIT]

                for op_type, ref in batch_ops:
                    batch.delete(ref)
                    if op_type == "session":
                        deleted_sessions += 1
                        logger.debug("Firestore: queued delete for expired session %s", ref.id)

                batch.commit()
                logger.debug("Firestore: committed batch of %d deletes", len(batch_ops))

            if deleted_sessions > 0:
                logger.info("Firestore: cleaned up %d expired sessions in %d batch(es)",
                           deleted_sessions, (len(delete_ops) + _BATCH_LIMIT - 1) // _BATCH_LIMIT)

            return deleted_sessions

        except Exception as e:
            logger.error("Firestore cleanup error: %s", e, exc_info=True)
            return 0
