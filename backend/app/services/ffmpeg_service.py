"""Service for FFmpeg operations.

Responsibilities:
- Probe video metadata (duration, resolution, fps)
- Extract audio from video files
- Cut and concatenate video segments
- Render final output with crossfades and audio normalization
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class FFmpegService:
    """Wraps FFmpeg/FFprobe CLI operations."""

    def __init__(self) -> None:
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.ffprobe_path = settings.FFPROBE_PATH

    async def _run_command(self, *args: str) -> tuple[bytes, bytes, int]:
        """Run a subprocess command and return (stdout, stderr, returncode)."""
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout, stderr, proc.returncode

    async def probe(self, file_path: str) -> dict:
        """Probe a media file and return its metadata.

        Args:
            file_path: Path to the media file.

        Returns:
            Dict with keys: duration_ms, width, height, fps, file_size_bytes.
        """
        stdout, stderr, returncode = await self._run_command(
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        )

        if returncode != 0:
            logger.warning("FFprobe failed for %s: %s", file_path, stderr.decode(errors="replace"))
            return {}

        data = json.loads(stdout.decode())
        metadata: dict = {
            "duration_ms": None,
            "width": None,
            "height": None,
            "fps": None,
            "file_size_bytes": None,
        }

        # Duration from format
        fmt = data.get("format", {})
        duration_str = fmt.get("duration")
        if duration_str:
            try:
                metadata["duration_ms"] = int(float(duration_str) * 1000)
            except (ValueError, TypeError):
                pass

        # File size
        try:
            metadata["file_size_bytes"] = os.path.getsize(file_path)
        except OSError:
            pass

        # Video stream info
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                metadata["width"] = stream.get("width")
                metadata["height"] = stream.get("height")
                r_frame_rate = stream.get("r_frame_rate", "")
                if r_frame_rate and "/" in r_frame_rate:
                    try:
                        num, den = r_frame_rate.split("/")
                        if int(den) != 0:
                            metadata["fps"] = round(int(num) / int(den), 3)
                    except (ValueError, ZeroDivisionError):
                        pass
                break

        return metadata

    async def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio track from a video file as WAV 16kHz mono.

        Args:
            video_path: Path to the source video.
            output_path: Path to write the extracted audio.

        Returns:
            Path to the extracted audio file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        _, stderr, returncode = await self._run_command(
            self.ffmpeg_path,
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            output_path,
        )

        if returncode != 0:
            error_msg = stderr.decode(errors="replace")
            logger.error("Audio extraction failed for %s: %s", video_path, error_msg)
            raise RuntimeError(f"FFmpeg audio extraction failed: {error_msg[:500]}")

        logger.info("Extracted audio: %s -> %s", video_path, output_path)
        return output_path

    async def extract_frame(self, video_path: str, timestamp_ms: int, output_path: str) -> str:
        """Extract a single frame as JPEG at the given timestamp.

        Args:
            video_path: Path to the source video.
            timestamp_ms: Timestamp in milliseconds.
            output_path: Path to write the frame JPEG.

        Returns:
            Path to the extracted frame.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        seconds = timestamp_ms / 1000.0
        timestamp_str = f"{seconds:.3f}"

        _, stderr, returncode = await self._run_command(
            self.ffmpeg_path,
            "-ss", timestamp_str,
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_path,
        )

        if returncode != 0:
            error_msg = stderr.decode(errors="replace")
            logger.error("Frame extraction failed: %s", error_msg)
            raise RuntimeError(f"FFmpeg frame extraction failed: {error_msg[:500]}")

        return output_path

    async def trim_segment(
        self, video_path: str, start_ms: int, end_ms: int, output_path: str
    ) -> str:
        """Trim a video segment with re-encoding.

        Args:
            video_path: Source video file.
            start_ms: Start time in milliseconds.
            end_ms: End time in milliseconds.
            output_path: Where to write the trimmed segment.

        Returns:
            Path to the output file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0

        _, stderr, returncode = await self._run_command(
            self.ffmpeg_path,
            "-ss", f"{start_sec:.3f}",
            "-i", video_path,
            "-t", f"{duration_sec:.3f}",
            "-c:v", "libx264",
            "-crf", "22",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-y",
            output_path,
        )

        if returncode != 0:
            error_msg = stderr.decode(errors="replace")
            logger.error("Trim failed for %s: %s", video_path, error_msg)
            raise RuntimeError(f"FFmpeg trim failed: {error_msg[:500]}")

        logger.info("Trimmed segment: %s [%d-%d ms] -> %s", video_path, start_ms, end_ms, output_path)
        return output_path

    async def cut_segment(
        self, input_path: str, output_path: str, start_ms: int, end_ms: int
    ) -> str:
        """Cut a segment from a media file (alias for trim_segment with swapped arg order).

        Args:
            input_path: Source media file.
            output_path: Where to write the cut segment.
            start_ms: Start time in milliseconds.
            end_ms: End time in milliseconds.

        Returns:
            Path to the output file.
        """
        return await self.trim_segment(input_path, start_ms, end_ms, output_path)

    async def concat_segments(self, segment_paths: list[str], output_path: str) -> str:
        """Concatenate multiple video segments using the concat demuxer.

        Args:
            segment_paths: List of video file paths to concatenate.
            output_path: Where to write the concatenated output.

        Returns:
            Path to the output file.
        """
        if not segment_paths:
            raise ValueError("No segments to concatenate")

        if len(segment_paths) == 1:
            # Just copy the single file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, shutil.copy2, segment_paths[0], output_path)
            return output_path

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create a concat list file
        concat_file = os.path.join(tempfile.gettempdir(), f"concat_{uuid.uuid4()}.txt")
        try:
            with open(concat_file, "w") as f:
                for path in segment_paths:
                    # Escape single quotes in path for FFmpeg concat format
                    escaped = path.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            _, stderr, returncode = await self._run_command(
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y",
                output_path,
            )

            if returncode != 0:
                error_msg = stderr.decode(errors="replace")
                logger.error("Concat failed: %s", error_msg)
                raise RuntimeError(f"FFmpeg concat failed: {error_msg[:500]}")

            logger.info("Concatenated %d segments -> %s", len(segment_paths), output_path)
            return output_path
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)

    async def concatenate(self, input_paths: list[str], output_path: str) -> str:
        """Concatenate multiple media files into one (alias for concat_segments).

        Args:
            input_paths: List of media file paths to concatenate.
            output_path: Where to write the concatenated output.

        Returns:
            Path to the output file.
        """
        return await self.concat_segments(input_paths, output_path)

    async def render_final(
        self,
        clips_with_ranges: list[dict],
        output_path: str,
    ) -> str:
        """Full render pipeline: trim kept ranges, concatenate, normalize audio.

        Args:
            clips_with_ranges: List of dicts with keys:
                - clip_path: path to the source clip video
                - ranges: list of (start_ms, end_ms) tuples for kept segments
            output_path: Where to write the final rendered video.

        Returns:
            Path to the final output file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="clipflow_render_")
        temp_segments: list[str] = []

        try:
            # Step 1: Trim each kept range to a temp file
            segment_idx = 0
            for clip_info in clips_with_ranges:
                clip_path = clip_info["clip_path"]
                ranges = clip_info["ranges"]

                for start_ms, end_ms in ranges:
                    temp_path = os.path.join(temp_dir, f"seg_{segment_idx:04d}.mp4")
                    await self.trim_segment(clip_path, start_ms, end_ms, temp_path)
                    temp_segments.append(temp_path)
                    segment_idx += 1

            if not temp_segments:
                raise ValueError("No segments to render - all content was cut")

            # Step 2: Concatenate all temp segments
            if len(temp_segments) == 1:
                concat_path = temp_segments[0]
            else:
                concat_path = os.path.join(temp_dir, "concatenated.mp4")
                await self.concat_segments(temp_segments, concat_path)

            # Step 3: Normalize audio and output final MP4
            _, stderr, returncode = await self._run_command(
                self.ffmpeg_path,
                "-i", concat_path,
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-c:v", "libx264",
                "-crf", "22",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                "-y",
                output_path,
            )

            if returncode != 0:
                error_msg = stderr.decode(errors="replace")
                logger.error("Final render failed: %s", error_msg)
                raise RuntimeError(f"FFmpeg final render failed: {error_msg[:500]}")

            logger.info("Rendered final video: %s (%d segments)", output_path, len(temp_segments))
            return output_path

        finally:
            # Clean up temp files
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                logger.warning("Failed to clean up temp dir: %s", temp_dir)


# Module-level singleton
ffmpeg_service = FFmpegService()
