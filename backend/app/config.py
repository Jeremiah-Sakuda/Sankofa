import os
from dotenv import load_dotenv

load_dotenv()


def _parse_cors_origins() -> list[str]:
    """Parse CORS origins from env: comma-separated list, or single FRONTEND_URL."""
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    url = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
    return [url] if url else []


class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GOOGLE_GENAI_USE_VERTEXAI: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # CORS: use CORS_ORIGINS for multiple origins, or FRONTEND_URL for single
    CORS_ORIGINS: list[str] = _parse_cors_origins()

    GEMINI_IMAGE_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_PLANNING_MODEL: str = "gemini-2.0-flash"
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"

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


settings = Settings()
