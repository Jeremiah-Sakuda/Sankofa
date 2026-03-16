import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.rate_limiter import limiter
from app.routes import audio, intake, live, narrative

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
        try:
            if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"},
            )

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    yield


# Allow request body up to 1MB to prevent large payload abuse
app = FastAPI(
    title="Sankofa API",
    description="Ancestral Heritage Narrator — transforming personal inputs into immersive heritage narratives",
    version="0.1.0",
    lifespan=lifespan,
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(intake.router)
app.include_router(narrative.router)
app.include_router(audio.router)
app.include_router(live.router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "sankofa-api",
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    return {
        "message": "Sankofa — Ancestral Heritage Narrator",
        "docs": "/docs",
        "health": "/api/health",
    }
