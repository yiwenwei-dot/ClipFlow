import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db
from app.routers import clips, export, processing, projects, transcripts


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database and storage directories on startup."""
    # Ensure storage directories exist
    os.makedirs(os.path.join(settings.STORAGE_PATH, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_PATH, "processed"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_PATH, "exports"), exist_ok=True)

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
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding the maximum upload size."""

    async def dispatch(self, request: Request, call_next):
        # Only enforce on upload endpoints
        content_length = request.headers.get("content-length")
        if content_length:
            max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
            if int(content_length) > max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB."
                    },
                )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)

# Include routers
app.include_router(projects.router)
app.include_router(clips.router)
app.include_router(transcripts.router)
app.include_router(processing.router)
app.include_router(export.router)


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
