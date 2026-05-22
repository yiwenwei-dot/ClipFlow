"""Service for merging video segments into a final export.

Responsibilities:
- Build FFmpeg filter graph from kept segments
- Concatenate video segments across clips
- Handle audio/video sync
- Write final output file
- Create Export record
"""

import logging
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.clip import Clip
from app.models.export import Export
from app.models.project import Project
from app.models.segment import TranscriptSegment
from app.services.cutting_service import compute_kept_ranges
from app.services.ffmpeg_service import ffmpeg_service

logger = logging.getLogger(__name__)


class MergeService:
    """Merges kept video segments into a final rendered output."""

    def __init__(self) -> None:
        self.storage_path = settings.STORAGE_PATH

    async def merge_project(
        self,
        project_id: str,
        db: AsyncSession,
        output_format: str = "mp4",
    ) -> Export:
        """Orchestrate the full render for a project.

        Steps:
        1. Get all clips in sequence order
        2. For each clip, get segments and compute kept ranges
        3. Call ffmpeg_service.render_final with clips and ranges
        4. Create Export record with output file metadata
        5. Update project status to "exported"

        Args:
            project_id: The project to render.
            db: Async database session.
            output_format: Output file format (default: "mp4").

        Returns:
            The created Export record.
        """
        # Step 1: Get project and clips
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        result = await db.execute(
            select(Clip)
            .where(Clip.project_id == project_id)
            .order_by(Clip.sequence_order)
        )
        clips = list(result.scalars().all())

        if not clips:
            raise ValueError(f"No clips found for project {project_id}")

        # Step 2: Build clips_with_ranges for render
        clips_with_ranges: list[dict] = []

        for clip in clips:
            # Get segments for this clip
            seg_result = await db.execute(
                select(TranscriptSegment)
                .where(TranscriptSegment.clip_id == clip.id)
                .order_by(TranscriptSegment.start_ms)
            )
            segments = list(seg_result.scalars().all())

            if not segments:
                # If no segments (not yet transcribed), include the whole clip
                if clip.duration_ms:
                    ranges = [(0, clip.duration_ms)]
                else:
                    # Try probing for duration
                    metadata = await ffmpeg_service.probe(clip.storage_path)
                    duration = metadata.get("duration_ms")
                    if duration:
                        ranges = [(0, duration)]
                    else:
                        logger.warning("Cannot determine duration for clip %s, skipping", clip.id)
                        continue
            else:
                ranges = compute_kept_ranges(segments)

            if ranges:
                clips_with_ranges.append({
                    "clip_path": clip.storage_path,
                    "ranges": ranges,
                })

        if not clips_with_ranges:
            raise ValueError("No content to render - all segments are cut")

        # Step 3: Render final video
        export_id = str(uuid.uuid4())
        export_dir = os.path.join(self.storage_path, "exports")
        os.makedirs(export_dir, exist_ok=True)
        output_path = os.path.join(export_dir, f"{export_id}.{output_format}")

        await ffmpeg_service.render_final(clips_with_ranges, output_path)

        # Step 4: Get output metadata and create Export record
        output_metadata = await ffmpeg_service.probe(output_path)
        file_size = None
        try:
            file_size = os.path.getsize(output_path)
        except OSError:
            pass

        export = Export(
            id=export_id,
            project_id=project_id,
            storage_path=output_path,
            format=output_format,
            file_size_bytes=file_size,
            duration_ms=output_metadata.get("duration_ms"),
        )

        resolution = None
        w = output_metadata.get("width")
        h = output_metadata.get("height")
        if w and h:
            resolution = f"{w}x{h}"
            export.resolution = resolution

        db.add(export)

        # Step 5: Update project status
        project.status = "exported"

        await db.flush()
        await db.refresh(export)

        logger.info(
            "Rendered project %s -> %s (duration: %s ms)",
            project_id, output_path, output_metadata.get("duration_ms"),
        )

        return export

    async def render_project(self, project_id: str, output_format: str = "mp4") -> str:
        """Render the final video by merging all kept segments.

        Note: This requires a DB session. Use merge_project() instead.

        Args:
            project_id: The project to render.
            output_format: Output file format (e.g., 'mp4', 'webm').

        Returns:
            Path to the rendered output file.
        """
        raise NotImplementedError(
            "Use merge_project() with a DB session instead"
        )

    async def build_segment_list(self, project_id: str) -> list[dict]:
        """Build the ordered list of time ranges to include in the final video.

        Note: This requires a DB session. Use merge_project() instead.

        Args:
            project_id: The project to process.

        Returns:
            List of dicts with clip_id, start_ms, end_ms for each kept segment.
        """
        raise NotImplementedError(
            "Use merge_project() with a DB session instead"
        )


# Module-level singleton
merge_service = MergeService()
