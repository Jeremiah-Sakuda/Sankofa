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

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def count(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)
