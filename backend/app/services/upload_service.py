"""Service for handling file uploads and storage management.

Responsibilities:
- Save uploaded video files to the local filesystem
- Validate file types and sizes
- Generate unique storage paths
- Clean up orphaned files
"""

from app.config import settings


class UploadService:
    """Handles file upload storage operations."""

    def __init__(self) -> None:
        self.storage_path = settings.STORAGE_PATH
        self.max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    async def save_upload(self, project_id: str, filename: str, content: bytes) -> str:
        """Save an uploaded file and return its storage path.

        Args:
            project_id: The project this file belongs to.
            filename: Original filename from the upload.
            content: Raw file bytes.

        Returns:
            The relative storage path where the file was saved.
        """
        raise NotImplementedError

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from storage.

        Args:
            storage_path: Path to the file to delete.
        """
        raise NotImplementedError

    async def validate_file(self, filename: str, size_bytes: int) -> None:
        """Validate file type and size constraints.

        Args:
            filename: Original filename.
            size_bytes: File size in bytes.

        Raises:
            ValueError: If validation fails.
        """
        raise NotImplementedError
