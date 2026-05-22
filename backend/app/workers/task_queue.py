"""Simple background task runner for processing pipelines.

Orchestrates the transcription -> analysis flow for a project,
updating ProcessingJob progress along the way.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.clip import Clip
from app.models.processing_job import ProcessingJob
from app.models.project import Project
from app.models.segment import TranscriptSegment
from app.models.speaker import Speaker
from app.services.analysis_service import analysis_service
from app.services.merge_service import merge_service
from app.services.transcription_service import transcription_service

logger = logging.getLogger(__name__)

# Speaker color palette for auto-assignment
SPEAKER_COLORS = [
    "#3B82F6", "#EF4444", "#10B981", "#F59E0B",
    "#8B5CF6", "#EC4899", "#06B6D4", "#F97316",
]


async def run_processing_pipeline(project_id: str, job_id: str) -> None:
    """Run the full transcribe -> analyze pipeline for a project.

    This function manages its own DB session since it runs as a background task.

    Args:
        project_id: The project to process.
        job_id: The ProcessingJob ID to update with progress.
    """
    async with async_session_factory() as db:
        try:
            # Mark job as running
            job = await db.get(ProcessingJob, job_id)
            if not job:
                logger.error("Job %s not found", job_id)
                return

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.progress_pct = 0
            await db.commit()

            # Get project
            project = await db.get(Project, project_id)
            if not project:
                await _fail_job(db, job_id, "Project not found")
                return

            # Get clips
            result = await db.execute(
                select(Clip)
                .where(Clip.project_id == project_id)
                .order_by(Clip.sequence_order)
            )
            clips = list(result.scalars().all())

            if not clips:
                await _fail_job(db, job_id, "No clips found in project")
                return

            total_clips = len(clips)

            # Phase 1: Transcription (0% - 60%)
            logger.info("Starting transcription for project %s (%d clips)", project_id, total_clips)
            all_segments: list[TranscriptSegment] = []
            speaker_cache: dict[str, str] = {}  # speaker_label -> speaker_id

            for idx, clip in enumerate(clips):
                try:
                    # Transcribe the clip
                    segment_dicts = await transcription_service.transcribe_clip(
                        clip.storage_path, project_id
                    )

                    # Create Speaker and TranscriptSegment records
                    for seg_dict in segment_dicts:
                        speaker_label = seg_dict.get("speaker_label", "0")
                        speaker_id = await _get_or_create_speaker(
                            db, project_id, speaker_label, speaker_cache
                        )

                        segment = TranscriptSegment(
                            id=str(uuid.uuid4()),
                            clip_id=clip.id,
                            speaker_id=speaker_id,
                            start_ms=seg_dict["start_ms"],
                            end_ms=seg_dict["end_ms"],
                            text=seg_dict["text"],
                            confidence=seg_dict.get("confidence"),
                            word_timestamps=seg_dict.get("word_timestamps"),
                            segment_type=seg_dict.get("segment_type", "speech"),
                            cut_decision="keep",
                        )
                        db.add(segment)
                        all_segments.append(segment)

                    # Update clip status
                    clip.status = "transcribed"

                    # Update progress
                    pct = int(((idx + 1) / total_clips) * 60)
                    await _update_progress(db, job_id, pct)

                except Exception:
                    logger.exception("Failed to transcribe clip %s", clip.id)
                    # Continue with other clips

            await db.commit()

            # Reload segments from DB to get fresh state
            seg_result = await db.execute(
                select(TranscriptSegment)
                .join(Clip, TranscriptSegment.clip_id == Clip.id)
                .where(Clip.project_id == project_id)
                .order_by(Clip.sequence_order, TranscriptSegment.start_ms)
            )
            all_segments = list(seg_result.scalars().all())

            # Phase 2: Filler + Silence Detection (60% - 80%)
            logger.info("Starting filler/silence detection for project %s", project_id)
            try:
                filler_results = analysis_service.detect_fillers(
                    all_segments,
                    filler_words=project.filler_words,
                    silence_threshold_ms=project.silence_threshold_ms,
                )

                # Apply filler/silence updates
                for result_item in filler_results:
                    if "segment_id" in result_item and "updates" in result_item:
                        seg = await db.get(TranscriptSegment, result_item["segment_id"])
                        if seg:
                            for field, value in result_item["updates"].items():
                                setattr(seg, field, value)

                    elif "new_segment" in result_item:
                        new_seg_data = result_item["new_segment"]
                        silence_seg = TranscriptSegment(
                            id=str(uuid.uuid4()),
                            **new_seg_data,
                        )
                        db.add(silence_seg)

                await db.commit()
                await _update_progress(db, job_id, 80)

            except Exception:
                logger.exception("Filler/silence detection failed for project %s", project_id)
                # Continue with duplicate detection

            # Phase 3: Duplicate Detection (80% - 95%)
            logger.info("Starting duplicate detection for project %s", project_id)
            try:
                # Reload segments
                seg_result = await db.execute(
                    select(TranscriptSegment)
                    .join(Clip, TranscriptSegment.clip_id == Clip.id)
                    .where(Clip.project_id == project_id)
                    .where(TranscriptSegment.segment_type == "speech")
                    .order_by(Clip.sequence_order, TranscriptSegment.start_ms)
                )
                speech_segments = list(seg_result.scalars().all())

                dup_results = await analysis_service.detect_repeated_takes(
                    speech_segments, project_id
                )

                for dup_item in dup_results:
                    if "segment_id" in dup_item and "updates" in dup_item:
                        seg = await db.get(TranscriptSegment, dup_item["segment_id"])
                        if seg:
                            for field, value in dup_item["updates"].items():
                                setattr(seg, field, value)

                await db.commit()
                await _update_progress(db, job_id, 95)

            except Exception:
                logger.exception("Duplicate detection failed for project %s", project_id)

            # Mark project as analyzed
            project = await db.get(Project, project_id)
            if project:
                project.status = "analyzed"
                await db.commit()

            # Mark job as completed
            job = await db.get(ProcessingJob, job_id)
            if job:
                job.status = "completed"
                job.progress_pct = 100
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

            logger.info("Processing pipeline completed for project %s", project_id)

        except Exception as e:
            logger.exception("Processing pipeline failed for project %s", project_id)
            await _fail_job(db, job_id, str(e))


async def run_render_pipeline(project_id: str, job_id: str) -> None:
    """Run the render pipeline for a project.

    Args:
        project_id: The project to render.
        job_id: The ProcessingJob ID to update with progress.
    """
    async with async_session_factory() as db:
        try:
            job = await db.get(ProcessingJob, job_id)
            if not job:
                logger.error("Job %s not found", job_id)
                return

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.progress_pct = 10
            await db.commit()

            # Run the merge
            await merge_service.merge_project(project_id, db)
            await db.commit()

            # Mark job as completed
            job = await db.get(ProcessingJob, job_id)
            if job:
                job.status = "completed"
                job.progress_pct = 100
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

            logger.info("Render pipeline completed for project %s", project_id)

        except Exception as e:
            logger.exception("Render pipeline failed for project %s", project_id)
            await _fail_job(db, job_id, str(e))


async def _get_or_create_speaker(
    db: AsyncSession,
    project_id: str,
    speaker_label: str,
    cache: dict[str, str],
) -> str:
    """Get or create a Speaker record, using a cache to avoid duplicates.

    Returns the speaker ID.
    """
    cache_key = f"{project_id}:{speaker_label}"
    if cache_key in cache:
        return cache[cache_key]

    # Check if speaker already exists
    result = await db.execute(
        select(Speaker).where(
            Speaker.project_id == project_id,
            Speaker.label == f"Speaker {speaker_label}",
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        cache[cache_key] = existing.id
        return existing.id

    # Create new speaker
    speaker_idx = len(cache)
    color = SPEAKER_COLORS[speaker_idx % len(SPEAKER_COLORS)]
    speaker = Speaker(
        id=str(uuid.uuid4()),
        project_id=project_id,
        label=f"Speaker {speaker_label}",
        color=color,
    )
    db.add(speaker)
    await db.flush()

    cache[cache_key] = speaker.id
    return speaker.id


async def _update_progress(db: AsyncSession, job_id: str, pct: int) -> None:
    """Update the progress of a processing job."""
    job = await db.get(ProcessingJob, job_id)
    if job:
        job.progress_pct = pct
        await db.commit()


async def _fail_job(db: AsyncSession, job_id: str, error_message: str) -> None:
    """Mark a processing job as failed."""
    try:
        job = await db.get(ProcessingJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = error_message[:1000]  # Truncate long errors
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception:
        logger.exception("Failed to update job %s status to failed", job_id)
