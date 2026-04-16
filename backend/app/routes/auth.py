"""Authentication routes for Google OAuth via Firebase."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from app.models.user import User
from app.rate_limiter import limiter
from app.store.user_store import user_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Firebase Admin SDK - initialized lazily
_firebase_app = None


def _get_firebase_app():
    """Get or initialize Firebase Admin SDK."""
    global _firebase_app
    if _firebase_app is None:
        try:
            import firebase_admin
            from firebase_admin import credentials
            from app.config import settings

            # In GCP environment, use default credentials
            # Locally, requires GOOGLE_APPLICATION_CREDENTIALS env var
            if settings.GOOGLE_CLOUD_PROJECT:
                cred = credentials.ApplicationDefault()
                _firebase_app = firebase_admin.initialize_app(cred, {
                    "projectId": settings.GOOGLE_CLOUD_PROJECT,
                })
            else:
                logger.warning("Firebase Auth not configured - GOOGLE_CLOUD_PROJECT not set")
                return None
        except Exception as e:
            logger.error("Failed to initialize Firebase Admin: %s", e)
            return None
    return _firebase_app


async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[User]:
    """Extract and verify Firebase ID token from Authorization header.

    Returns None if no Authorization header (allows anonymous access).
    Raises 401 if token is provided but invalid (prevents silent auth failures).
    """
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.split(" ", 1)[1]

    try:
        from firebase_admin import auth

        app = _get_firebase_app()
        if app is None:
            # Firebase not configured - allow anonymous
            logger.warning("Firebase not configured, treating as anonymous")
            return None

        decoded = auth.verify_id_token(token, app=app)
        user_id = decoded["uid"]

        # Get or create user
        user = user_store.get(user_id)
        if user:
            return user

        # Create new user from Firebase token
        return User(
            user_id=user_id,
            email=decoded.get("email", ""),
            display_name=decoded.get("name"),
            avatar_url=decoded.get("picture"),
        )
    except Exception as e:
        # Token was provided but invalid - reject with 401
        logger.warning("Token verification failed: %s", type(e).__name__)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require authenticated user. Raises 401 if not authenticated."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


class LoginRequest(BaseModel):
    """Request body for login - contains Firebase ID token."""
    id_token: str


class UserResponse(BaseModel):
    """User profile response."""
    user_id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


@router.post("/login", response_model=UserResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    """Verify Firebase ID token and create/update user record.

    The frontend should obtain an ID token from Firebase Auth (Google sign-in)
    and send it here to establish the session.
    """
    try:
        from firebase_admin import auth

        app = _get_firebase_app()
        if app is None:
            raise HTTPException(
                status_code=503,
                detail="Authentication service not available"
            )

        # Verify the ID token
        decoded = auth.verify_id_token(body.id_token, app=app)
        user_id = decoded["uid"]

        # Create or update user
        user = User(
            user_id=user_id,
            email=decoded.get("email", ""),
            display_name=decoded.get("name"),
            avatar_url=decoded.get("picture"),
        )

        # Check if user exists and preserve created_at
        existing = user_store.get(user_id)
        if existing:
            user.created_at = existing.created_at

        user = user_store.create_or_update(user)

        logger.info("User logged in: %s", user_id)

        return UserResponse(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error: %s", e, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_me(request: Request, user: User = Depends(require_user)):
    """Get current user profile."""
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
    )


@router.post("/logout")
async def logout(user: User = Depends(require_user)):
    """Logout endpoint - client should clear their token.

    This is primarily for analytics/logging. Firebase tokens are stateless,
    so the client is responsible for clearing their local token.
    """
    logger.info("User logged out: %s", user.user_id)
    return {"message": "Logged out successfully"}
