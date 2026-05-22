import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.clip import Clip
from app.models.project import Project
from app.schemas.clip import ClipReorderRequest, ClipResponse

router = APIRouter(prefix="/api/projects/{project_id}/clips", tags=["clips"])


@router.post("", response_model=ClipResponse, status_code=201)
async def upload_clip(
    project_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> Clip:
    # Verify project exists
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine next sequence order
    result = await db.execute(
        select(func.coalesce(func.max(Clip.sequence_order), 0)).where(
            Clip.project_id == project_id
        )
    )
    next_order = result.scalar_one() + 1

    # Save file to storage
    clip_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "video.mp4")[1]
    storage_dir = os.path.join(settings.STORAGE_PATH, "uploads", project_id)
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = os.path.join(storage_dir, f"{clip_id}{ext}")

    file_size = 0
    async with aiofiles.open(storage_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(chunk)
            await f.write(chunk)

    clip = Clip(
        id=clip_id,
        project_id=project_id,
        filename=file.filename or "video.mp4",
        storage_path=storage_path,
        sequence_order=next_order,
        file_size_bytes=file_size,
    )
    db.add(clip)
    await db.flush()
    await db.refresh(clip)
    return clip


@router.get("", response_model=list[ClipResponse])
async def list_clips(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[Clip]:
    result = await db.execute(
        select(Clip)
        .where(Clip.project_id == project_id)
        .order_by(Clip.sequence_order)
    )
    return list(result.scalars().all())


@router.patch("/reorder", response_model=list[ClipResponse])
async def reorder_clips(
    project_id: str,
    data: ClipReorderRequest,
    db: AsyncSession = Depends(get_db),
) -> list[Clip]:
    for item in data.clips:
        clip = await db.get(Clip, item.id)
        if clip and clip.project_id == project_id:
            clip.sequence_order = item.sequence_order

    await db.flush()

    result = await db.execute(
        select(Clip)
        .where(Clip.project_id == project_id)
        .order_by(Clip.sequence_order)
    )
    return list(result.scalars().all())


@router.delete("/{clip_id}", status_code=204)
async def delete_clip(
    project_id: str, clip_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    clip = await db.get(Clip, clip_id)
    if not clip or clip.project_id != project_id:
        raise HTTPException(status_code=404, detail="Clip not found")

    # Remove file from disk
    if os.path.exists(clip.storage_path):
        os.remove(clip.storage_path)

    await db.delete(clip)


@router.get("/{clip_id}/stream")
async def stream_clip(
    project_id: str, clip_id: str, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    clip = await db.get(Clip, clip_id)
    if not clip or clip.project_id != project_id:
        raise HTTPException(status_code=404, detail="Clip not found")
    if not os.path.exists(clip.storage_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    return FileResponse(
        clip.storage_path,
        media_type="video/mp4",
        filename=clip.filename,
    )
