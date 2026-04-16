"""Firestore-backed session store. Sessions in main collection; segments in subcollection to stay under 1 MiB doc limit."""

import logging
import time
from typing import Optional

from google.cloud import firestore

from app.config import settings
from app.models.schemas import NarrativeSegment, UserInput
from app.models.session import Session

logger = logging.getLogger(__name__)

# Session TTL in seconds (24 hours)
_SESSION_TTL_SECONDS = 24 * 60 * 60


def _get_client() -> firestore.Client:
    return firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)


def _session_to_doc(session: Session, include_ttl: bool = False) -> dict:
    """Session document fields (no segments; those go in subcollection)."""
    doc = {
        "user_input": session.user_input.model_dump(),
        "narrative_context": session.narrative_context,
        "is_generating": session.is_generating,
        "generating_started_at": session.generating_started_at,
        "arc_outline": session.arc_outline,
        "created_at": session.created_at,
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
    )


class FirestoreSessionStore:
    """Session store backed by Firestore. Main doc per session; segments in subcollection."""

    def __init__(self):
        self._client: Optional[firestore.Client] = None
        self._collection_name = settings.FIRESTORE_SESSIONS_COLLECTION

    def _client_or_init(self) -> firestore.Client:
        if self._client is None:
            self._client = _get_client()
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
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session.session_id)
            doc_ref.update(_session_to_doc(session))
            # Replace segments subcollection
            seg_coll = doc_ref.collection("segments")
            for seg_doc in seg_coll.stream():
                seg_doc.reference.delete()
            for seg in session.segments:
                seg_dict = seg.model_dump()
                # Strip media_data that exceeds Firestore's 1 MiB field limit.
                # Audio/image blobs are already streamed to the client via SSE,
                # so Firestore only needs the metadata for session recovery.
                if seg_dict.get("media_data") and len(seg_dict["media_data"]) > 900_000:
                    seg_dict["media_data"] = None
                seg_coll.document(str(seg.sequence)).set(seg_dict)
            logger.debug("Firestore: updated session %s (%d segments)", session.session_id, len(session.segments))
        except Exception as e:
            logger.error("Firestore update error: %s", e, exc_info=True)
            raise RuntimeError("Failed to update session in data store.") from e

    def exists(self, session_id: str) -> bool:
        try:
            doc_ref = self._client_or_init().collection(self._collection_name).document(session_id)
            return doc_ref.get().exists
        except Exception as e:
            logger.error("Firestore exists error: %s", e, exc_info=True)
            raise RuntimeError("Failed to verify session existence in data store.") from e

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
