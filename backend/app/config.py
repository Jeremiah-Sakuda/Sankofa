import os

from dotenv import load_dotenv

load_dotenv()


def _parse_cors_origins() -> list[str]:
    """Parse CORS origins from env: comma or semicolon-separated list, or single FRONTEND_URL."""
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        # Support both comma and semicolon as delimiters (semicolon needed for gcloud --set-env-vars)
        origins = []
        for part in raw.replace(";", ",").split(","):
            origin = part.strip()
            if origin:
                origins.append(origin)
        return origins
    url = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
    return [url] if url else []


class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GOOGLE_GENAI_USE_VERTEXAI: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "").strip()  # Strip spaces/newlines
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # CORS: use CORS_ORIGINS for multiple origins, or FRONTEND_URL for single
    CORS_ORIGINS: list[str] = _parse_cors_origins()

    # Model IDs for Gemini API (aistudio.google.com). Match https://ai.google.dev/gemini-api/docs/models
    # Planning: text-only. Narrative: must support image+text output (e.g. Nano Banana). TTS: audio output.
    GEMINI_PLANNING_MODEL: str = os.getenv("GEMINI_PLANNING_MODEL", "gemini-2.5-flash")
    GEMINI_LIVE_MODEL: str = os.getenv(
        "GEMINI_LIVE_MODEL",
        "gemini-live-2.5-flash-native-audio"
        if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
        else "gemini-2.5-flash-native-audio-preview-12-2025",
    )
    GEMINI_IMAGE_MODEL: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")  # Nano Banana: image+text
    GEMINI_TTS_MODEL: str = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

    # Session store: in-memory (default) or Firestore
    USE_FIRESTORE: bool = os.getenv("USE_FIRESTORE", "false").lower() == "true"
    FIRESTORE_SESSIONS_COLLECTION: str = os.getenv("FIRESTORE_SESSIONS_COLLECTION", "sessions")

    # Analytics access key (for /api/stats endpoint)
    ANALYTICS_KEY: str = os.getenv("ANALYTICS_KEY", "sankofa-stats")

    # Stripe integration for contributions (tip jar)
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    ENABLE_CONTRIBUTIONS: bool = os.getenv("ENABLE_CONTRIBUTIONS", "false").lower() == "true"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    def validate(self) -> None:
        """Validate required config for runtime. Raises ValueError if invalid."""
        if self.GOOGLE_GENAI_USE_VERTEXAI:
            if not self.GOOGLE_CLOUD_PROJECT:
                raise ValueError("GOOGLE_CLOUD_PROJECT is required when GOOGLE_GENAI_USE_VERTEXAI is true")
        else:
            if not self.GOOGLE_API_KEY and self.is_production:
                raise ValueError("GOOGLE_API_KEY is required in production when not using Vertex AI")
        if not self.CORS_ORIGINS and self.is_production:
            raise ValueError("At least one CORS origin (FRONTEND_URL or CORS_ORIGINS) is required in production")
        if self.USE_FIRESTORE and not self.GOOGLE_CLOUD_PROJECT:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when USE_FIRESTORE is true")
        # Require strong analytics key in production
        if self.is_production and self.ANALYTICS_KEY == "sankofa-stats":
            raise ValueError("ANALYTICS_KEY must be set to a unique secret in production (not the default)")


settings = Settings()
