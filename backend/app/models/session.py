from typing import Optional
from dataclasses import dataclass, field
from app.models.schemas import UserInput, NarrativeSegment


@dataclass
class Session:
    session_id: str
    user_input: UserInput
    segments: list[NarrativeSegment] = field(default_factory=list)
    narrative_context: str = ""
    is_generating: bool = False
    arc_outline: Optional[dict] = None


class SessionStore:
    """In-memory session storage. Replace with Firestore for production."""

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


session_store = SessionStore()
