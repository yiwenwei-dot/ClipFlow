import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.clip import Clip
from app.models.project import Project
from app.schemas.clip import ClipReorderRequest, ClipResponse
from app.services.upload_service import upload_service

# Map common video extensions to MIME types
VIDEO_MIME_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".m4v": "video/x-m4v",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
}

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

    # Validate file
    filename = file.filename or "video.mp4"
    try:
        # Read file size for validation (peek at content-length or read)
        content_type = file.content_type or ""
        # We validate after reading since UploadFile may not have size upfront
    except Exception:
        pass

    # Determine next sequence order
    result = await db.execute(
        select(func.coalesce(func.max(Clip.sequence_order), 0)).where(
            Clip.project_id == project_id
        )
    )
    next_order = result.scalar_one() + 1

    # Save file to storage using upload_service unique naming
    clip_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1]
    storage_dir = os.path.join(settings.STORAGE_PATH, "uploads", project_id)
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = os.path.join(storage_dir, f"{clip_id}{ext}")

    file_size = 0
    async with aiofiles.open(storage_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            file_size += len(chunk)
            await f.write(chunk)

    # Validate file type and size
    try:
        await upload_service.validate_file(filename, file_size)
    except ValueError as e:
        # Clean up the file we just wrote
        if os.path.exists(storage_path):
            os.remove(storage_path)
        raise HTTPException(status_code=400, detail=str(e))

    # Extract video metadata using FFprobe
    metadata = await upload_service.extract_metadata(storage_path)

    clip = Clip(
        id=clip_id,
        project_id=project_id,
        filename=filename,
        storage_path=storage_path,
        sequence_order=next_order,
        file_size_bytes=metadata.get("file_size_bytes") or file_size,
        duration_ms=metadata.get("duration_ms"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        fps=metadata.get("fps"),
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
    project_id: str,
    clip_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream a video clip with HTTP Range request support for seeking."""
    clip = await db.get(Clip, clip_id)
    if not clip or clip.project_id != project_id:
        raise HTTPException(status_code=404, detail="Clip not found")
    if not os.path.exists(clip.storage_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    file_size = os.path.getsize(clip.storage_path)

    # Determine content type from file extension
    ext = os.path.splitext(clip.storage_path)[1].lower()
    content_type = VIDEO_MIME_TYPES.get(ext, "video/mp4")

    # Parse Range header
    range_header = request.headers.get("range")

    if range_header:
        # Parse "bytes=start-end" format
        try:
            range_spec = range_header.replace("bytes=", "")
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
        except (ValueError, IndexError):
            raise HTTPException(status_code=416, detail="Invalid Range header")

        # Validate range
        if start >= file_size or end >= file_size or start > end:
            raise HTTPException(
                status_code=416,
                detail="Range not satisfiable",
            )

        content_length = end - start + 1

        async def ranged_file_stream():
            async with aiofiles.open(clip.storage_path, "rb") as f:
                await f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            ranged_file_stream(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Disposition": f'inline; filename="{clip.filename}"',
            },
        )

    # No Range header - stream full file
    async def full_file_stream():
        async with aiofiles.open(clip.storage_path, "rb") as f:
            while chunk := await f.read(1024 * 1024):  # 1MB chunks
                yield chunk

    return StreamingResponse(
        full_file_stream(),
        media_type=content_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{clip.filename}"',
        },
    )
