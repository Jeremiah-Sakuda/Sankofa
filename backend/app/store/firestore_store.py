"""Firestore-backed session store. Sessions in main collection; segments in subcollection to stay under 1 MiB doc limit."""

import logging
from typing import Optional

from google.cloud import firestore

from app.config import settings
from app.models.schemas import NarrativeSegment, UserInput
from app.models.session import Session

logger = logging.getLogger(__name__)


def _get_client() -> firestore.Client:
    return firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)


def _session_to_doc(session: Session) -> dict:
    """Session document fields (no segments; those go in subcollection)."""
    return {
        "user_input": session.user_input.model_dump(),
        "narrative_context": session.narrative_context,
        "is_generating": session.is_generating,
        "arc_outline": session.arc_outline,
    }


def _doc_to_session(session_id: str, data: dict, segments: list[NarrativeSegment]) -> Session:
    return Session(
        session_id=session_id,
        user_input=UserInput.model_validate(data["user_input"]),
        segments=segments,
        narrative_context=data.get("narrative_context") or "",
        is_generating=data.get("is_generating") or False,
        arc_outline=data.get("arc_outline"),
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
            doc_ref.set(_session_to_doc(session))
            logger.info("Firestore: created session %s", session_id)
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
                seg_coll.document(str(seg.sequence)).set(seg.model_dump())
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
