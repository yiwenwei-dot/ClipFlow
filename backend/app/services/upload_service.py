"""Service for handling file uploads and storage management.

Responsibilities:
- Save uploaded video files to the local filesystem
- Validate file types and sizes
- Generate unique storage paths
- Extract video metadata via FFprobe
- Clean up orphaned files
"""

import asyncio
import json
import logging
import os
import uuid

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv"}


class UploadService:
    """Handles file upload storage operations."""

    def __init__(self) -> None:
        self.storage_path = settings.STORAGE_PATH
        self.max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        self.ffprobe_path = settings.FFPROBE_PATH

    async def save_upload(self, project_id: str, filename: str, content: bytes) -> str:
        """Save an uploaded file and return its storage path.

        Args:
            project_id: The project this file belongs to.
            filename: Original filename from the upload.
            content: Raw file bytes.

        Returns:
            The storage path where the file was saved.
        """
        await self.validate_file(filename, len(content))

        # Create unique filename to avoid collisions
        ext = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{ext}"

        upload_dir = os.path.join(self.storage_path, "uploads", project_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, unique_filename)

        # Write file to disk using executor to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_file, file_path, content)

        logger.info("Saved upload: %s -> %s", filename, file_path)
        return file_path

    def _write_file(self, path: str, content: bytes) -> None:
        """Synchronously write file content to disk."""
        with open(path, "wb") as f:
            f.write(content)

    async def extract_metadata(self, file_path: str) -> dict:
        """Extract video metadata using FFprobe.

        Args:
            file_path: Path to the video file on disk.

        Returns:
            Dict with keys: duration_ms, width, height, fps, file_size_bytes.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(
                    "FFprobe failed for %s: %s", file_path, stderr.decode(errors="replace")
                )
                return self._fallback_metadata(file_path)

            data = json.loads(stdout.decode())
            return self._parse_probe_output(data, file_path)
        except FileNotFoundError:
            logger.warning("FFprobe not found at %s, returning fallback metadata", self.ffprobe_path)
            return self._fallback_metadata(file_path)
        except Exception:
            logger.exception("Error probing file %s", file_path)
            return self._fallback_metadata(file_path)

    def _parse_probe_output(self, data: dict, file_path: str) -> dict:
        """Parse FFprobe JSON output into a clean metadata dict."""
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
            size_str = fmt.get("size")
            if size_str:
                try:
                    metadata["file_size_bytes"] = int(size_str)
                except (ValueError, TypeError):
                    pass

        # Find video stream for width, height, fps
        streams = data.get("streams", [])
        for stream in streams:
            if stream.get("codec_type") == "video":
                metadata["width"] = stream.get("width")
                metadata["height"] = stream.get("height")

                # Parse fps from r_frame_rate (e.g., "30000/1001" or "30/1")
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

    def _fallback_metadata(self, file_path: str) -> dict:
        """Return basic metadata when FFprobe is unavailable."""
        file_size = None
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            pass

        return {
            "duration_ms": None,
            "width": None,
            "height": None,
            "fps": None,
            "file_size_bytes": file_size,
        }

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from storage.

        Args:
            storage_path: Path to the file to delete.
        """
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, os.remove, storage_path)
            logger.info("Deleted file: %s", storage_path)
        except FileNotFoundError:
            logger.warning("File not found for deletion: %s", storage_path)
        except OSError:
            logger.exception("Failed to delete file: %s", storage_path)

    async def validate_file(self, filename: str, size_bytes: int) -> None:
        """Validate file type and size constraints.

        Args:
            filename: Original filename.
            size_bytes: File size in bytes.

        Raises:
            ValueError: If validation fails.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        if size_bytes > self.max_size_bytes:
            max_mb = self.max_size_bytes / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum of {max_mb:.0f} MB")

        if size_bytes == 0:
            raise ValueError("File is empty")


# Module-level singleton
upload_service = UploadService()
