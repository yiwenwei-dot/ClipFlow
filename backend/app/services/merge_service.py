"""Service for merging video segments into a final export.

Responsibilities:
- Build FFmpeg filter graph from kept segments
- Concatenate video segments across clips
- Handle audio/video sync
- Write final output file
"""


class MergeService:
    """Merges kept video segments into a final rendered output."""

    async def render_project(self, project_id: str, output_format: str = "mp4") -> str:
        """Render the final video by merging all kept segments.

        Args:
            project_id: The project to render.
            output_format: Output file format (e.g., 'mp4', 'webm').

        Returns:
            Path to the rendered output file.
        """
        raise NotImplementedError

    async def build_segment_list(self, project_id: str) -> list[dict]:
        """Build the ordered list of time ranges to include in the final video.

        Args:
            project_id: The project to process.

        Returns:
            List of dicts with clip_id, start_ms, end_ms for each kept segment.
        """
        raise NotImplementedError
