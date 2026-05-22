from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import clips, export, processing, projects, transcripts


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="ClipFlow API",
    description="AI-powered video editing backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(clips.router)
app.include_router(transcripts.router)
app.include_router(processing.router)
app.include_router(export.router)


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
