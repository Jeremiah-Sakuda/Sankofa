"""Session store implementations. session_store is the configured backend (in-memory or Firestore)."""

from app.config import settings

if settings.USE_FIRESTORE:
    from app.store.firestore_store import FirestoreSessionStore
    session_store = FirestoreSessionStore()
else:
    from app.models.session import InMemorySessionStore
    session_store = InMemorySessionStore()

__all__ = ["session_store"]
