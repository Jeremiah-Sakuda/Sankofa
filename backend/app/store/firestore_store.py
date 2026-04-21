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
    """Session document fields (no segments; those go in subcollection)."""
    doc = {
        "user_input": session.user_input.model_dump(),
        "narrative_context": session.narrative_context,
        "is_generating": session.is_generating,
        "generating_started_at": session.generating_started_at,
        "arc_outline": session.arc_outline,
        "created_at": session.created_at,
        "owner_id": getattr(session, "owner_id", None),
        "is_public": getattr(session, "is_public", False),
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
        """
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session_id)
            seg_coll = doc_ref.collection("segments")
            seg_dict = segment.model_dump()
            # Strip media_data that exceeds Firestore's 1 MiB field limit.
            if seg_dict.get("media_data") and len(seg_dict["media_data"]) > 900_000:
                seg_dict["media_data"] = None
            seg_coll.document(str(segment.sequence)).set(seg_dict)
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
        """Delete expired sessions and their segments.

        Args:
            batch_size: Maximum number of sessions to delete in one call

        Returns:
            Number of sessions deleted
        """
        try:
            now = time.time()
            collection = self._client_or_init().collection(self._collection_name)

            # Query for expired sessions
            expired_query = (
                collection
                .where(filter=firestore.FieldFilter("expires_at", "<", now))
                .limit(batch_size)
            )

            deleted_count = 0
            for doc in expired_query.stream():
                session_id = doc.id
                doc_ref = collection.document(session_id)

                # Delete segments subcollection first
                seg_coll = doc_ref.collection("segments")
                for seg_doc in seg_coll.stream():
                    seg_doc.reference.delete()

                # Delete the session document
                doc_ref.delete()
                deleted_count += 1
                logger.debug("Firestore: deleted expired session %s", session_id)

            if deleted_count > 0:
                logger.info("Firestore: cleaned up %d expired sessions", deleted_count)

            return deleted_count

        except Exception as e:
            logger.error("Firestore cleanup error: %s", e, exc_info=True)
            return 0
