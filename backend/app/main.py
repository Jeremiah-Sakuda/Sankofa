import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.rate_limiter import limiter
from app.routes import audio, auth, contribute, intake, narrative, share
from app.services.analytics import get_aggregate_stats
from app.services.gemini_service import check_gemini_health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Max request body size (1MB) to prevent abuse
MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related HTTP headers for production."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except (ValueError, TypeError):
                # Malformed Content-Length header - log and continue
                # The actual body size will be enforced by the server
                logger.warning(
                    "Malformed Content-Length header: %s (continuing with request)",
                    content_length[:50] if len(content_length) < 100 else content_length[:50] + "..."
                )

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS: enforce HTTPS for 1 year, include subdomains
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy for API responses (JSON)
        # - default-src 'none': API responses shouldn't load any resources
        # - frame-ancestors 'none': prevent embedding in iframes (clickjacking)
        # Note: Full CSP should be set on the frontend (Next.js) for HTML pages
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Permissions-Policy: disable sensitive browser features not needed
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        return response


async def _session_cleanup_task():
    """Background task that periodically cleans up expired sessions."""
    import asyncio

    from app.store import session_store
    from app.store.firestore_store import FirestoreSessionStore

    # Only run cleanup for Firestore store
    if not isinstance(session_store, FirestoreSessionStore):
        logger.info("[cleanup] Session cleanup disabled (not using Firestore)")
        return

    cleanup_interval = 60 * 60  # 1 hour
    logger.info("[cleanup] Session cleanup task started (interval: %d seconds)", cleanup_interval)

    while True:
        try:
            await asyncio.sleep(cleanup_interval)
            deleted = session_store.cleanup_expired()
            if deleted > 0:
                logger.info("[cleanup] Deleted %d expired sessions", deleted)
        except asyncio.CancelledError:
            logger.info("[cleanup] Session cleanup task cancelled")
            break
        except Exception as e:
            logger.error("[cleanup] Error during session cleanup: %s", e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    try:
        settings.validate()
    except ValueError as e:
        if settings.is_production:
            raise
        logger.warning("Config validation skipped in non-production: %s", e)
    # Log Gemini API key status at startup (no key value printed)
    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        logger.info("Gemini: using Vertex AI (project=%s)", settings.GOOGLE_CLOUD_PROJECT or "?")
    else:
        key = settings.GOOGLE_API_KEY
        if key:
            logger.info("Gemini: API key present (length=%d). Source: aistudio.google.com/apikey", len(key))
        else:
            logger.warning("Gemini: GOOGLE_API_KEY is empty. Set it in backend/.env for narrative generation.")
    if settings.USE_FIRESTORE:
        logger.info("Session store: Firestore (project=%s, collection=%s)", settings.GOOGLE_CLOUD_PROJECT, settings.FIRESTORE_SESSIONS_COLLECTION)
    else:
        logger.info("Session store: in-memory")

    # Start background cleanup task for Firestore sessions
    cleanup_task = asyncio.create_task(_session_cleanup_task())

    yield

    # Cancel cleanup task on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# Allow request body up to 1MB to prevent large payload abuse
# Disable OpenAPI docs in production to reduce attack surface
app = FastAPI(
    title="Sankofa API",
    description="Ancestral Heritage Narrator — transforming personal inputs into immersive heritage narratives",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

# Security headers first (outer layer)
app.add_middleware(SecurityHeadersMiddleware)

# CORS: use configured origins; in dev allow common local ports if no CORS_ORIGINS set
_cors_origins = list(settings.CORS_ORIGINS)
if not _cors_origins:
    _cors_origins = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(intake.router)
app.include_router(narrative.router)
app.include_router(audio.router)
# app.include_router(live.router)  # Live Griot feature disabled for now
app.include_router(share.router)
app.include_router(contribute.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint with Gemini API status."""
    gemini_health = await check_gemini_health()

    # Overall status is degraded if Gemini is unavailable
    overall_status = "healthy" if gemini_health.get("available") else "degraded"

    return {
        "status": overall_status,
        "service": "sankofa-api",
        "version": "0.1.0",
        "gemini": {
            "available": gemini_health.get("available", False),
            "message": gemini_health.get("message", "Unknown"),
            "cached": gemini_health.get("cached", False),
        },
    }


@app.get("/api/stats")
@limiter.limit("10/minute")
async def analytics_stats(request: Request, authorization: str = Header(None)):
    """
    Aggregate analytics statistics (key-protected via Authorization header).

    Headers:
        Authorization: Bearer <ANALYTICS_KEY>
    """
    # Extract key from Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"error": "Authorization header required (Bearer <key>)"}
        )

    key = authorization.split(" ", 1)[1]
    if not hmac.compare_digest(key, settings.ANALYTICS_KEY):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid access key"}
        )

    stats = await get_aggregate_stats()
    return stats


@app.get("/")
async def root():
    return {
        "message": "Sankofa — Ancestral Heritage Narrator",
        "docs": "/docs",
        "health": "/api/health",
    }
