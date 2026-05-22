import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.export import Export
from app.models.processing_job import ProcessingJob
from app.models.project import Project
from app.workers.task_queue import run_render_pipeline

router = APIRouter(prefix="/api/projects/{project_id}/exports", tags=["exports"])


class ExportRequest(BaseModel):
    format: str = "mp4"
    resolution: str | None = None


class ExportResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    storage_path: str
    format: str
    resolution: str | None = None
    file_size_bytes: int | None = None
    duration_ms: int | None = None


@router.post("", response_model=ExportResponse, status_code=202)
async def start_export(
    project_id: str,
    data: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Export:
    """Start an export/render job.

    Creates a ProcessingJob to track progress and launches the render pipeline
    in the background. The Export record is created by the merge_service once
    rendering completes.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create a processing job to track the render
    from datetime import datetime, timezone

    job = ProcessingJob(
        id=str(uuid.uuid4()),
        project_id=project_id,
        job_type="render",
        status="queued",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)

    # Create a placeholder export record so we can return it immediately
    export_id = str(uuid.uuid4())
    storage_path = os.path.join("storage", "exports", f"{export_id}.{data.format}")

    export = Export(
        id=export_id,
        project_id=project_id,
        storage_path=storage_path,
        format=data.format,
        resolution=data.resolution,
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)

    # Launch render in background
    background_tasks.add_task(run_render_pipeline, project_id, job.id)

    return export


@router.get("", response_model=list[ExportResponse])
async def list_exports(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[Export]:
    result = await db.execute(
        select(Export)
        .where(Export.project_id == project_id)
        .order_by(Export.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{export_id}/download")
async def download_export(
    project_id: str, export_id: str, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    export = await db.get(Export, export_id)
    if not export or export.project_id != project_id:
        raise HTTPException(status_code=404, detail="Export not found")
    if not os.path.exists(export.storage_path):
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    return FileResponse(
        export.storage_path,
        media_type=f"video/{export.format}",
        filename=f"clipflow-export-{export_id}.{export.format}",
    )
