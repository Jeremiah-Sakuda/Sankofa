import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

from app.models.schemas import NarrativeSegment, UserInput

logger = logging.getLogger(__name__)

# If is_generating has been True for longer than this, treat it as stale
_GENERATING_STALE_SECONDS = 300  # 5 minutes

# LRU cache limits for in-memory store
_MAX_SESSIONS = 100
_WARN_THRESHOLD = 50


@dataclass
class Session:
    session_id: str
    user_input: UserInput
    segments: list[NarrativeSegment] = field(default_factory=list)
    narrative_context: str = ""
    is_generating: bool = False
    generating_started_at: float = 0.0
    arc_outline: Optional[dict] = None
    created_at: float = field(default_factory=time.time)
    owner_id: Optional[str] = None
    is_public: bool = False

    @property
    def is_generating_stale(self) -> bool:
        """True if is_generating has been set for too long (stale lock)."""
        if not self.is_generating:
            return False
        return (time.time() - self.generating_started_at) > _GENERATING_STALE_SECONDS


class InMemorySessionStore:
    """In-memory session storage with LRU eviction.

    Used when USE_FIRESTORE is false (development mode).
    Automatically evicts oldest non-generating sessions when capacity is reached.
    """

    def __init__(self, max_sessions: int = _MAX_SESSIONS):
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._max_sessions = max_sessions

    def _evict_if_needed(self) -> None:
        """Evict oldest non-generating sessions if at capacity."""
        if len(self._sessions) < self._max_sessions:
            return

        # Find candidates for eviction (not currently generating)
        eviction_candidates = [
            sid for sid, sess in self._sessions.items()
            if not sess.is_generating
        ]

        if not eviction_candidates:
            logger.warning(
                "[session-store] At capacity (%d) with all sessions generating; "
                "cannot evict", len(self._sessions)
            )
            return

        # Evict the oldest candidate (first in OrderedDict that's not generating)
        to_evict = eviction_candidates[0]
        del self._sessions[to_evict]
        logger.info("[session-store] Evicted session %s (LRU)", to_evict)

    def create(self, session_id: str, user_input: UserInput) -> Session:
        # Check capacity and warn/evict
        if len(self._sessions) >= _WARN_THRESHOLD:
            logger.warning(
                "[session-store] Session count (%d) exceeds warning threshold (%d)",
                len(self._sessions), _WARN_THRESHOLD
            )

        self._evict_if_needed()

        session = Session(session_id=session_id, user_input=user_input)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session:
            # Move to end (most recently accessed) for LRU
            self._sessions.move_to_end(session_id)
        return session

    def update(self, session: Session) -> None:
        self._sessions[session.session_id] = session
        # Move to end (most recently used)
        self._sessions.move_to_end(session.session_id)

    def update_metadata(self, session: Session) -> None:
        """Update session metadata. For in-memory store, same as update()."""
        self.update(session)

    def append_segment(self, session_id: str, segment: NarrativeSegment) -> None:
        """Append a segment to the session. For in-memory store, finds and appends."""
        session = self._sessions.get(session_id)
        if session:
            # Only append if not already present (idempotent)
            if not any(s.sequence == segment.sequence for s in session.segments):
                session.segments.append(segment)
            self._sessions.move_to_end(session_id)

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def list_by_owner(self, owner_id: str, limit: int = 50) -> list[Session]:
        """List sessions owned by a user, sorted by created_at descending."""
        owned = [s for s in self._sessions.values() if s.owner_id == owner_id]
        owned.sort(key=lambda s: s.created_at, reverse=True)
        return owned[:limit]

    def list_by_owner_summary(self, owner_id: str, limit: int = 50) -> list[dict]:
        """List session summaries owned by a user, sorted by created_at descending.

        Returns dict summaries matching FirestoreSessionStore.list_by_owner_summary()
        for API consistency.

        Returns list of dicts with keys:
            session_id, family_name, region, era, created_at, segment_count,
            first_image_data, first_image_type, arc_title
        """
        sessions = self.list_by_owner(owner_id, limit)
        summaries = []

        for session in sessions:
            # Find first image for thumbnail
            first_image = next(
                (s for s in session.segments if s.type == "image" and s.media_data),
                None
            )

            # Get arc title if available
            arc_title = None
            if session.arc_outline and isinstance(session.arc_outline, dict):
                arc_title = session.arc_outline.get("title")

            summaries.append({
                "session_id": session.session_id,
                "family_name": session.user_input.family_name,
                "region": session.user_input.region_of_origin,
                "era": session.user_input.time_period,
                "created_at": session.created_at,
                "segment_count": len(session.segments),
                "first_image_data": first_image.media_data if first_image else None,
                "first_image_type": first_image.media_type if first_image else None,
                "arc_title": arc_title,
            })

        return summaries

    def set_owner(self, session_id: str, owner_id: str) -> bool:
        """Set the owner of a session. Returns True on success."""
        session = self._sessions.get(session_id)
        if session:
            session.owner_id = owner_id
            return True
        return False

    def count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)
