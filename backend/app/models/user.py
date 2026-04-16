"""User model for authenticated users."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """Represents an authenticated user."""
    user_id: str  # Firebase UID
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_login_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore storage."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from Firestore document."""
        return cls(
            user_id=data["user_id"],
            email=data["email"],
            display_name=data.get("display_name"),
            avatar_url=data.get("avatar_url"),
            created_at=data.get("created_at", time.time()),
            last_login_at=data.get("last_login_at", time.time()),
        )
