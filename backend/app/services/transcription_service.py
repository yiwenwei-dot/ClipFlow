"""Service for audio transcription via Deepgram Nova-2.

Responsibilities:
- Send audio to Deepgram API for transcription
- Handle diarization (multi-speaker detection)
- Parse Deepgram response into TranscriptSegment records
- Manage word-level timestamps
- Gracefully mock when no API key is available
"""

import logging
import os
import uuid

import httpx

from app.config import settings
from app.services.ffmpeg_service import ffmpeg_service

logger = logging.getLogger(__name__)

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"


class TranscriptionService:
    """Integrates with Deepgram for speech-to-text transcription."""

    def __init__(self) -> None:
        self.api_key = settings.DEEPGRAM_API_KEY
        self.storage_path = settings.STORAGE_PATH

    async def transcribe_clip(self, clip_path: str, project_id: str) -> list[dict]:
        """Transcribe a video/audio clip and return segment data.

        Args:
            clip_path: Path to the video/audio file on disk.
            project_id: The project this clip belongs to.

        Returns:
            List of segment dictionaries ready for DB insertion.
            Each dict has: start_ms, end_ms, text, confidence, word_timestamps,
                          speaker_label, segment_type.
        """
        # Step 1: Extract audio from video clip
        audio_dir = os.path.join(self.storage_path, "processed", project_id)
        os.makedirs(audio_dir, exist_ok=True)
        audio_filename = f"{uuid.uuid4()}.wav"
        audio_path = os.path.join(audio_dir, audio_filename)

        try:
            await ffmpeg_service.extract_audio(clip_path, audio_path)
        except RuntimeError:
            logger.warning("Audio extraction failed, attempting direct transcription of %s", clip_path)
            audio_path = clip_path

        # Step 2: Transcribe via Deepgram or mock
        if self.api_key:
            segments = await self._transcribe_deepgram(audio_path)
        else:
            logger.warning("DEEPGRAM_API_KEY not set, using mock transcription")
            segments = self._mock_transcription()

        # Clean up extracted audio if we created one
        if audio_path != clip_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass

        return segments

    async def _transcribe_deepgram(self, audio_path: str) -> list[dict]:
        """Call Deepgram API with the audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Parsed list of segment dictionaries.
        """
        params = {
            "model": "nova-2",
            "diarize": "true",
            "punctuate": "true",
            "utterances": "true",
            "smart_format": "true",
        }

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(audio_path, "rb") as audio_file:
                    audio_data = audio_file.read()

                response = await client.post(
                    DEEPGRAM_API_URL,
                    params=params,
                    headers=headers,
                    content=audio_data,
                )

                if response.status_code != 200:
                    logger.error(
                        "Deepgram API error %d: %s",
                        response.status_code,
                        response.text[:500],
                    )
                    raise RuntimeError(
                        f"Deepgram API returned status {response.status_code}"
                    )

                data = response.json()
                return self._parse_deepgram_response(data)

        except httpx.HTTPError as e:
            logger.error("HTTP error calling Deepgram: %s", str(e))
            raise RuntimeError(f"Failed to call Deepgram API: {e}") from e

    def _parse_deepgram_response(self, data: dict) -> list[dict]:
        """Parse Deepgram JSON response into segment dictionaries.

        Uses utterances for segment boundaries, with word-level timestamps.
        """
        segments: list[dict] = []

        results = data.get("results", {})
        utterances = results.get("utterances", [])

        if not utterances:
            # Fallback to alternatives/paragraphs if no utterances
            channels = results.get("channels", [])
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    # Use the transcript as a single segment
                    alt = alternatives[0]
                    transcript = alt.get("transcript", "")
                    if transcript.strip():
                        words = alt.get("words", [])
                        segments.append({
                            "start_ms": int(words[0]["start"] * 1000) if words else 0,
                            "end_ms": int(words[-1]["end"] * 1000) if words else 0,
                            "text": transcript,
                            "confidence": alt.get("confidence", 0.0),
                            "word_timestamps": self._extract_word_timestamps(words),
                            "speaker_label": str(words[0].get("speaker", 0)) if words else "0",
                            "segment_type": "speech",
                        })
            return segments

        for utterance in utterances:
            start_sec = utterance.get("start", 0)
            end_sec = utterance.get("end", 0)
            text = utterance.get("transcript", "")
            confidence = utterance.get("confidence", 0.0)
            speaker = utterance.get("speaker", 0)
            words = utterance.get("words", [])

            if not text.strip():
                continue

            segments.append({
                "start_ms": int(start_sec * 1000),
                "end_ms": int(end_sec * 1000),
                "text": text,
                "confidence": confidence,
                "word_timestamps": self._extract_word_timestamps(words),
                "speaker_label": str(speaker),
                "segment_type": "speech",
            })

        return segments

    def _extract_word_timestamps(self, words: list[dict]) -> dict:
        """Extract word-level timestamps from Deepgram words array.

        Returns a dict with a 'words' key containing list of word objects.
        """
        word_data = []
        for word in words:
            word_data.append({
                "word": word.get("word", ""),
                "start_ms": int(word.get("start", 0) * 1000),
                "end_ms": int(word.get("end", 0) * 1000),
                "confidence": word.get("confidence", 0.0),
                "speaker": word.get("speaker", 0),
            })
        return {"words": word_data}

    def _mock_transcription(self) -> list[dict]:
        """Generate mock transcription data for development without API key."""
        return [
            {
                "start_ms": 0,
                "end_ms": 3000,
                "text": "Hello, this is a mock transcription segment.",
                "confidence": 0.95,
                "word_timestamps": {
                    "words": [
                        {"word": "Hello,", "start_ms": 0, "end_ms": 500, "confidence": 0.98, "speaker": 0},
                        {"word": "this", "start_ms": 550, "end_ms": 750, "confidence": 0.96, "speaker": 0},
                        {"word": "is", "start_ms": 800, "end_ms": 900, "confidence": 0.99, "speaker": 0},
                        {"word": "a", "start_ms": 950, "end_ms": 1050, "confidence": 0.97, "speaker": 0},
                        {"word": "mock", "start_ms": 1100, "end_ms": 1400, "confidence": 0.94, "speaker": 0},
                        {"word": "transcription", "start_ms": 1450, "end_ms": 2100, "confidence": 0.93, "speaker": 0},
                        {"word": "segment.", "start_ms": 2150, "end_ms": 2800, "confidence": 0.95, "speaker": 0},
                    ]
                },
                "speaker_label": "0",
                "segment_type": "speech",
            },
            {
                "start_ms": 3500,
                "end_ms": 7000,
                "text": "Um, basically this is like the second segment you know.",
                "confidence": 0.89,
                "word_timestamps": {
                    "words": [
                        {"word": "Um,", "start_ms": 3500, "end_ms": 3800, "confidence": 0.85, "speaker": 0},
                        {"word": "basically", "start_ms": 3850, "end_ms": 4300, "confidence": 0.90, "speaker": 0},
                        {"word": "this", "start_ms": 4350, "end_ms": 4500, "confidence": 0.92, "speaker": 0},
                        {"word": "is", "start_ms": 4550, "end_ms": 4650, "confidence": 0.95, "speaker": 0},
                        {"word": "like", "start_ms": 4700, "end_ms": 4900, "confidence": 0.88, "speaker": 0},
                        {"word": "the", "start_ms": 4950, "end_ms": 5100, "confidence": 0.96, "speaker": 0},
                        {"word": "second", "start_ms": 5150, "end_ms": 5500, "confidence": 0.93, "speaker": 0},
                        {"word": "segment", "start_ms": 5550, "end_ms": 5900, "confidence": 0.91, "speaker": 0},
                        {"word": "you", "start_ms": 5950, "end_ms": 6100, "confidence": 0.94, "speaker": 0},
                        {"word": "know.", "start_ms": 6150, "end_ms": 6400, "confidence": 0.92, "speaker": 0},
                    ]
                },
                "speaker_label": "0",
                "segment_type": "speech",
            },
        ]

    async def transcribe_project(self, project_id: str) -> None:
        """Transcribe all clips in a project sequentially.

        This is a higher-level method that fetches clips from the DB.
        Use transcribe_clip for individual clip transcription in the worker.

        Args:
            project_id: The project to transcribe.
        """
        # This method is called from the task queue worker which handles DB access
        raise NotImplementedError(
            "Use transcribe_clip directly from the worker with proper DB context"
        )


# Module-level singleton
transcription_service = TranscriptionService()
