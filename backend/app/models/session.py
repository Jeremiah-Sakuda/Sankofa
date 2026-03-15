import time
from dataclasses import dataclass, field
from typing import Optional

from app.models.schemas import NarrativeSegment, UserInput

# If is_generating has been True for longer than this, treat it as stale
_GENERATING_STALE_SECONDS = 300  # 5 minutes


@dataclass
class Session:
    session_id: str
    user_input: UserInput
    segments: list[NarrativeSegment] = field(default_factory=list)
    narrative_context: str = ""
    is_generating: bool = False
    generating_started_at: float = 0.0
    arc_outline: Optional[dict] = None

    @property
    def is_generating_stale(self) -> bool:
        """True if is_generating has been set for too long (stale lock)."""
        if not self.is_generating:
            return False
        return (time.time() - self.generating_started_at) > _GENERATING_STALE_SECONDS


class InMemorySessionStore:
    """In-memory session storage. Used when USE_FIRESTORE is false."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, session_id: str, user_input: UserInput) -> Session:
        session = Session(session_id=session_id, user_input=user_input)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions
