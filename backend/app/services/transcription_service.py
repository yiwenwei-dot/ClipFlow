"""Service for audio transcription using WhisperX (local, free).

Falls back to faster-whisper if WhisperX is not installed.
No API keys required - runs entirely on local hardware.
"""

import logging
import os
import uuid

from app.config import settings
from app.services.ffmpeg_service import ffmpeg_service

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Transcribes audio using WhisperX (local Whisper + diarization)."""

    def __init__(self) -> None:
        self.storage_path = settings.STORAGE_PATH
        self._model = None
        self._device = "cpu"
        self._compute_type = "int8"
        self._model_size = "base"
        self._hf_token = os.environ.get("HF_TOKEN", "")

    def _get_model(self):
        """Lazy-load the WhisperX or faster-whisper model."""
        if self._model is not None:
            return self._model

        try:
            import whisperx
            self._model = whisperx.load_model(
                self._model_size,
                self._device,
                compute_type=self._compute_type,
            )
            self._backend = "whisperx"
            logger.info("Loaded WhisperX model (%s)", self._model_size)
        except ImportError:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                self._backend = "faster_whisper"
                logger.info("Loaded faster-whisper model (%s)", self._model_size)
            except ImportError:
                logger.warning("Neither whisperx nor faster-whisper installed, using mock")
                self._backend = "mock"
                self._model = "mock"

        return self._model

    async def transcribe_clip(self, clip_path: str, project_id: str) -> list[dict]:
        """Transcribe a video/audio clip and return segment data.

        Returns list of segment dicts with: start_ms, end_ms, text, confidence,
        word_timestamps, speaker_label, segment_type.
        """
        audio_dir = os.path.join(self.storage_path, "processed", project_id)
        os.makedirs(audio_dir, exist_ok=True)
        audio_filename = f"{uuid.uuid4()}.wav"
        audio_path = os.path.join(audio_dir, audio_filename)

        try:
            await ffmpeg_service.extract_audio(clip_path, audio_path)
        except RuntimeError:
            logger.warning("Audio extraction failed, attempting direct transcription")
            audio_path = clip_path

        model = self._get_model()

        if self._backend == "whisperx":
            segments = self._transcribe_whisperx(audio_path)
        elif self._backend == "faster_whisper":
            segments = self._transcribe_faster_whisper(audio_path)
        else:
            segments = self._mock_transcription()

        if audio_path != clip_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass

        return segments

    def _transcribe_whisperx(self, audio_path: str) -> list[dict]:
        """Transcribe using WhisperX with alignment and diarization."""
        import whisperx

        audio = whisperx.load_audio(audio_path)
        result = self._model.transcribe(audio, batch_size=8)

        # Align whisper output for word-level timestamps
        try:
            align_model, metadata = whisperx.load_align_model(
                language_code=result.get("language", "en"),
                device=self._device,
            )
            result = whisperx.align(
                result["segments"], align_model, metadata, audio, self._device,
                return_char_alignments=False,
            )
        except Exception:
            logger.warning("Alignment failed, using raw whisper timestamps")

        # Diarization (requires HF_TOKEN)
        if self._hf_token:
            try:
                diarize_model = whisperx.DiarizationPipeline(
                    use_auth_token=self._hf_token,
                    device=self._device,
                )
                diarize_segments = diarize_model(audio)
                result = whisperx.assign_word_speakers(diarize_segments, result)
            except Exception:
                logger.warning("Diarization failed, continuing without speaker labels")

        segments = []
        for seg in result.get("segments", []):
            word_timestamps = []
            for w in seg.get("words", []):
                word_timestamps.append({
                    "word": w.get("word", ""),
                    "start_ms": int(w.get("start", 0) * 1000),
                    "end_ms": int(w.get("end", 0) * 1000),
                    "confidence": w.get("score", 0.0),
                    "speaker": w.get("speaker", "SPEAKER_00"),
                })

            segments.append({
                "start_ms": int(seg.get("start", 0) * 1000),
                "end_ms": int(seg.get("end", 0) * 1000),
                "text": seg.get("text", "").strip(),
                "confidence": sum(w.get("score", 0) for w in seg.get("words", [])) / max(len(seg.get("words", [])), 1),
                "word_timestamps": {"words": word_timestamps},
                "speaker_label": seg.get("speaker", "SPEAKER_00"),
                "segment_type": "speech",
            })

        return segments

    def _transcribe_faster_whisper(self, audio_path: str) -> list[dict]:
        """Transcribe using faster-whisper (no diarization)."""
        segs, info = self._model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en",
        )

        segments = []
        for seg in segs:
            word_timestamps = []
            for w in (seg.words or []):
                word_timestamps.append({
                    "word": w.word,
                    "start_ms": int(w.start * 1000),
                    "end_ms": int(w.end * 1000),
                    "confidence": w.probability,
                    "speaker": "SPEAKER_00",
                })

            segments.append({
                "start_ms": int(seg.start * 1000),
                "end_ms": int(seg.end * 1000),
                "text": seg.text.strip(),
                "confidence": sum(w.probability for w in (seg.words or [])) / max(len(seg.words or []), 1),
                "word_timestamps": {"words": word_timestamps},
                "speaker_label": "SPEAKER_00",
                "segment_type": "speech",
            })

        return segments

    def _mock_transcription(self) -> list[dict]:
        """Mock transcription for development when no ML libs are installed."""
        return [
            {
                "start_ms": 0,
                "end_ms": 3000,
                "text": "Hello, this is a mock transcription segment.",
                "confidence": 0.95,
                "word_timestamps": {
                    "words": [
                        {"word": "Hello,", "start_ms": 0, "end_ms": 500, "confidence": 0.98, "speaker": "SPEAKER_00"},
                        {"word": "this", "start_ms": 550, "end_ms": 750, "confidence": 0.96, "speaker": "SPEAKER_00"},
                        {"word": "is", "start_ms": 800, "end_ms": 900, "confidence": 0.99, "speaker": "SPEAKER_00"},
                        {"word": "a", "start_ms": 950, "end_ms": 1050, "confidence": 0.97, "speaker": "SPEAKER_00"},
                        {"word": "mock", "start_ms": 1100, "end_ms": 1400, "confidence": 0.94, "speaker": "SPEAKER_00"},
                        {"word": "transcription", "start_ms": 1450, "end_ms": 2100, "confidence": 0.93, "speaker": "SPEAKER_00"},
                        {"word": "segment.", "start_ms": 2150, "end_ms": 2800, "confidence": 0.95, "speaker": "SPEAKER_00"},
                    ]
                },
                "speaker_label": "SPEAKER_00",
                "segment_type": "speech",
            },
            {
                "start_ms": 3500,
                "end_ms": 7000,
                "text": "Um, basically this is like the second segment you know.",
                "confidence": 0.89,
                "word_timestamps": {
                    "words": [
                        {"word": "Um,", "start_ms": 3500, "end_ms": 3800, "confidence": 0.85, "speaker": "SPEAKER_00"},
                        {"word": "basically", "start_ms": 3850, "end_ms": 4300, "confidence": 0.90, "speaker": "SPEAKER_00"},
                        {"word": "this", "start_ms": 4350, "end_ms": 4500, "confidence": 0.92, "speaker": "SPEAKER_00"},
                        {"word": "is", "start_ms": 4550, "end_ms": 4650, "confidence": 0.95, "speaker": "SPEAKER_00"},
                        {"word": "like", "start_ms": 4700, "end_ms": 4900, "confidence": 0.88, "speaker": "SPEAKER_00"},
                        {"word": "the", "start_ms": 4950, "end_ms": 5100, "confidence": 0.96, "speaker": "SPEAKER_00"},
                        {"word": "second", "start_ms": 5150, "end_ms": 5500, "confidence": 0.93, "speaker": "SPEAKER_00"},
                        {"word": "segment", "start_ms": 5550, "end_ms": 5900, "confidence": 0.91, "speaker": "SPEAKER_00"},
                        {"word": "you", "start_ms": 5950, "end_ms": 6100, "confidence": 0.94, "speaker": "SPEAKER_00"},
                        {"word": "know.", "start_ms": 6150, "end_ms": 6400, "confidence": 0.92, "speaker": "SPEAKER_00"},
                    ]
                },
                "speaker_label": "SPEAKER_00",
                "segment_type": "speech",
            },
        ]


# Module-level singleton
transcription_service = TranscriptionService()
