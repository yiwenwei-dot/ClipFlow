import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.processing_job import ProcessingJob
from app.models.project import Project
from app.schemas.processing import ProcessingJobResponse, ProcessingStatusResponse
from app.workers.task_queue import run_processing_pipeline, run_render_pipeline

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
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ProcessingJob:
    """Start transcription + analysis processing for the project."""
    job = await _create_job(project_id, "transcribe", db)

    # Update project status
    project = await db.get(Project, project_id)
    if project:
        project.status = "processing"

    # Launch background processing pipeline
    background_tasks.add_task(run_processing_pipeline, project_id, job.id)

    return job


@router.post("/analyze", response_model=ProcessingJobResponse, status_code=202)
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ProcessingJob:
    """Start AI analysis (filler detection, silence, duplicates) for the project.

    Note: The transcription endpoint already runs analysis after transcription.
    Use this endpoint to re-run analysis on already-transcribed segments.
    """
    job = await _create_job(project_id, "analyze", db)

    # Analysis is part of the processing pipeline; launch it
    background_tasks.add_task(run_processing_pipeline, project_id, job.id)

    return job


@router.post("/render", response_model=ProcessingJobResponse, status_code=202)
async def start_render(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ProcessingJob:
    """Start video rendering for the project."""
    job = await _create_job(project_id, "render", db)

    # Launch render pipeline in background
    background_tasks.add_task(run_render_pipeline, project_id, job.id)

    return job


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
        try:
            while True:
                # Poll the latest job status from DB
                try:
                    from app.database import async_session_factory

                    async with async_session_factory() as poll_db:
                        result = await poll_db.execute(
                            select(ProcessingJob)
                            .where(ProcessingJob.project_id == project_id)
                            .order_by(ProcessingJob.created_at.desc())
                        )
                        jobs = list(result.scalars().all())

                        if jobs:
                            latest = jobs[0]
                            data = json.dumps({
                                "project_id": project_id,
                                "job_id": latest.id,
                                "status": latest.status,
                                "progress_pct": latest.progress_pct,
                                "error_message": latest.error_message,
                            })
                        else:
                            data = json.dumps({
                                "project_id": project_id,
                                "status": "idle",
                                "progress_pct": 0,
                            })

                    yield f"data: {data}\n\n"

                    # Stop streaming if job is done
                    if jobs and latest.status in ("completed", "failed"):
                        return

                except Exception as e:
                    data = json.dumps({
                        "project_id": project_id,
                        "status": "error",
                        "error_message": str(e),
                    })
                    yield f"data: {data}\n\n"

                await asyncio.sleep(2)
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
