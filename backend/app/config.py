import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GOOGLE_GENAI_USE_VERTEXAI: bool = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "False").lower() == "true"
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    GEMINI_IMAGE_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_PLANNING_MODEL: str = "gemini-2.0-flash"
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"


settings = Settings()
