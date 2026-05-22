from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.clip import Clip
from app.models.segment import TranscriptSegment
from app.schemas.segment import BulkSegmentUpdateRequest, SegmentResponse, SegmentUpdateRequest

router = APIRouter(prefix="/api/projects/{project_id}", tags=["transcripts"])


@router.get("/transcript", response_model=list[SegmentResponse])
async def get_project_transcript(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[TranscriptSegment]:
    """Get all transcript segments for a project, ordered by clip sequence then start time."""
    result = await db.execute(
        select(TranscriptSegment)
        .join(Clip, TranscriptSegment.clip_id == Clip.id)
        .where(Clip.project_id == project_id)
        .order_by(Clip.sequence_order, TranscriptSegment.start_ms)
    )
    return list(result.scalars().all())


@router.get("/clips/{clip_id}/transcript", response_model=list[SegmentResponse])
async def get_clip_transcript(
    project_id: str, clip_id: str, db: AsyncSession = Depends(get_db)
) -> list[TranscriptSegment]:
    """Get transcript segments for a specific clip."""
    # Verify clip belongs to project
    clip = await db.get(Clip, clip_id)
    if not clip or clip.project_id != project_id:
        raise HTTPException(status_code=404, detail="Clip not found")

    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.clip_id == clip_id)
        .order_by(TranscriptSegment.start_ms)
    )
    return list(result.scalars().all())


@router.patch("/segments/{segment_id}", response_model=SegmentResponse)
async def update_segment(
    project_id: str,
    segment_id: str,
    data: SegmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> TranscriptSegment:
    """Update a single transcript segment (e.g., change cut decision)."""
    segment = await db.get(TranscriptSegment, segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # Verify segment belongs to project via clip
    clip = await db.get(Clip, segment.clip_id)
    if not clip or clip.project_id != project_id:
        raise HTTPException(status_code=404, detail="Segment not found in project")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(segment, field, value)

    await db.flush()
    await db.refresh(segment)
    return segment


@router.patch("/segments", response_model=list[SegmentResponse])
async def bulk_update_segments(
    project_id: str,
    data: BulkSegmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> list[TranscriptSegment]:
    """Bulk update cut decisions for multiple segments."""
    updated = []
    for segment_id in data.segment_ids:
        segment = await db.get(TranscriptSegment, segment_id)
        if segment:
            segment.cut_decision = data.cut_decision
            updated.append(segment)

    await db.flush()
    for seg in updated:
        await db.refresh(seg)
    return updated
