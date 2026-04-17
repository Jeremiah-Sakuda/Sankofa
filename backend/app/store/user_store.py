"""Firestore-backed user store for authenticated users."""

import logging
import time
from typing import Optional

from google.cloud import firestore

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


def _get_client() -> firestore.Client:
    return firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)


class UserStore:
    """User store backed by Firestore."""

    def __init__(self):
        self._client: Optional[firestore.Client] = None
        self._collection_name = "users"

    def _client_or_init(self) -> firestore.Client:
        if self._client is None:
            self._client = _get_client()
        return self._client

    @property
    def _users(self) -> firestore.CollectionReference:
        return self._client_or_init().collection(self._collection_name)

    def get(self, user_id: str) -> Optional[User]:
        """Get user by ID. Returns None if not found."""
        try:
            doc = self._users.document(user_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            if not data:
                return None
            return User.from_dict(data)
        except Exception as e:
            logger.error("UserStore get error: %s", e, exc_info=True)
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email. Returns None if not found."""
        try:
            docs = self._users.where("email", "==", email).limit(1).stream()
            for doc in docs:
                data = doc.to_dict()
                if data:
                    return User.from_dict(data)
            return None
        except Exception as e:
            logger.error("UserStore get_by_email error: %s", e, exc_info=True)
            return None

    def create_or_update(self, user: User) -> User:
        """Create or update user. Returns the user."""
        try:
            user.last_login_at = time.time()
            self._users.document(user.user_id).set(user.to_dict(), merge=True)
            logger.info("UserStore: created/updated user %s", user.user_id)
            return user
        except Exception as e:
            logger.error("UserStore create_or_update error: %s", e, exc_info=True)
            raise RuntimeError("Failed to save user.") from e

    def delete(self, user_id: str) -> None:
        """Delete user by ID."""
        try:
            self._users.document(user_id).delete()
            logger.info("UserStore: deleted user %s", user_id)
        except Exception as e:
            logger.error("UserStore delete error: %s", e, exc_info=True)
            raise RuntimeError("Failed to delete user.") from e


# Singleton instance — only initialize Firestore-backed store in production
if settings.USE_FIRESTORE:
    user_store = UserStore()
else:
    # In-memory stub for local development without Firestore
    class _InMemoryUserStore:
        """Stub user store for local development. Auth features require USE_FIRESTORE=true."""

        def __init__(self):
            self._users: dict[str, User] = {}
            logger.warning("UserStore: using in-memory stub (auth features limited)")

        def get(self, user_id: str):
            return self._users.get(user_id)

        def get_by_email(self, email: str):
            for u in self._users.values():
                if u.email == email:
                    return u
            return None

        def create_or_update(self, user: User):
            import time
            user.last_login_at = time.time()
            self._users[user.user_id] = user
            return user

        def delete(self, user_id: str):
            self._users.pop(user_id, None)

    user_store = _InMemoryUserStore()  # type: ignore[assignment]
