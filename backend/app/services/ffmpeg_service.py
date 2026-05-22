"""Service for FFmpeg operations.

Responsibilities:
- Probe video metadata (duration, resolution, fps)
- Extract audio from video files
- Cut and concatenate video segments
- Transcode to different formats/resolutions
"""

from app.config import settings


class FFmpegService:
    """Wraps FFmpeg/FFprobe CLI operations."""

    def __init__(self) -> None:
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.ffprobe_path = settings.FFPROBE_PATH

    async def probe(self, file_path: str) -> dict:
        """Probe a media file and return its metadata.

        Args:
            file_path: Path to the media file.

        Returns:
            Dict with keys: duration_ms, width, height, fps, codec, etc.
        """
        raise NotImplementedError

    async def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio track from a video file.

        Args:
            video_path: Path to the source video.
            output_path: Path to write the extracted audio.

        Returns:
            Path to the extracted audio file.
        """
        raise NotImplementedError

    async def cut_segment(
        self, input_path: str, output_path: str, start_ms: int, end_ms: int
    ) -> str:
        """Cut a segment from a media file.

        Args:
            input_path: Source media file.
            output_path: Where to write the cut segment.
            start_ms: Start time in milliseconds.
            end_ms: End time in milliseconds.

        Returns:
            Path to the output file.
        """
        raise NotImplementedError

    async def concatenate(self, input_paths: list[str], output_path: str) -> str:
        """Concatenate multiple media files into one.

        Args:
            input_paths: List of media file paths to concatenate.
            output_path: Where to write the concatenated output.

        Returns:
            Path to the output file.
        """
        raise NotImplementedError
