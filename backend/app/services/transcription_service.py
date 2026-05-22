"""Service for audio transcription via Deepgram Nova-2.

Responsibilities:
- Send audio to Deepgram API for transcription
- Handle diarization (multi-speaker detection)
- Parse Deepgram response into TranscriptSegment records
- Manage word-level timestamps
"""


class TranscriptionService:
    """Integrates with Deepgram for speech-to-text transcription."""

    async def transcribe_clip(self, clip_id: str, audio_path: str) -> list[dict]:
        """Transcribe an audio/video file and return segment data.

        Args:
            clip_id: The clip being transcribed.
            audio_path: Path to the audio/video file.

        Returns:
            List of segment dictionaries ready for DB insertion.
        """
        raise NotImplementedError

    async def transcribe_project(self, project_id: str) -> None:
        """Transcribe all clips in a project sequentially.

        Args:
            project_id: The project to transcribe.
        """
        raise NotImplementedError
