import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import intake, narrative, audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sankofa API",
    description="Ancestral Heritage Narrator — transforming personal inputs into immersive heritage narratives",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intake.router)
app.include_router(narrative.router)
app.include_router(audio.router)


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
