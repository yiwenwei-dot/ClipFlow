import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.processing_job import ProcessingJob
from app.models.project import Project
from app.schemas.processing import ProcessingJobResponse, ProcessingStatusResponse

router = APIRouter(prefix="/api/projects/{project_id}/processing", tags=["processing"])


async def _create_job(
    project_id: str, job_type: str, db: AsyncSession
) -> ProcessingJob:
    """Create a processing job and return it."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = ProcessingJob(
        id=str(uuid.uuid4()),
        project_id=project_id,
        job_type=job_type,
        status="queued",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


@router.post("/transcribe", response_model=ProcessingJobResponse, status_code=202)
async def start_transcription(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> ProcessingJob:
    """Start transcription processing for the project."""
    return await _create_job(project_id, "transcribe", db)


@router.post("/analyze", response_model=ProcessingJobResponse, status_code=202)
async def start_analysis(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> ProcessingJob:
    """Start AI analysis (filler detection, silence, duplicates) for the project."""
    return await _create_job(project_id, "analyze", db)


@router.post("/render", response_model=ProcessingJobResponse, status_code=202)
async def start_render(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> ProcessingJob:
    """Start video rendering for the project."""
    return await _create_job(project_id, "render", db)


@router.get("/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get the processing status for all jobs in a project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.project_id == project_id)
        .order_by(ProcessingJob.created_at.desc())
    )
    jobs = list(result.scalars().all())

    # Compute overall status
    if not jobs:
        overall_status = "idle"
        overall_progress = 0
    elif any(j.status == "failed" for j in jobs):
        overall_status = "failed"
        overall_progress = 0
    elif all(j.status == "completed" for j in jobs):
        overall_status = "completed"
        overall_progress = 100
    elif any(j.status in ("queued", "running") for j in jobs):
        overall_status = "running"
        total = sum(j.progress_pct for j in jobs)
        overall_progress = total // len(jobs) if jobs else 0
    else:
        overall_status = "idle"
        overall_progress = 0

    return {
        "project_id": project_id,
        "jobs": jobs,
        "overall_status": overall_status,
        "overall_progress_pct": overall_progress,
    }


@router.get("/status/stream")
async def stream_processing_status(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """SSE endpoint for real-time processing status updates."""

    async def event_generator():
        # In a real implementation, this would watch for job updates.
        # For now, send a heartbeat every 5 seconds as a stub.
        try:
            while True:
                data = json.dumps(
                    {"project_id": project_id, "status": "polling", "progress_pct": 0}
                )
                yield f"data: {data}\n\n"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
