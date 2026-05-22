"""Service for AI-powered content analysis using local models.

Uses sentence-transformers for duplicate detection (no API keys needed).
Falls back to TF-IDF cosine similarity if sentence-transformers is not installed.
"""

import logging
import uuid

from app.config import settings
from app.models.segment import TranscriptSegment

logger = logging.getLogger(__name__)

DEFAULT_FILLER_WORDS = [
    "um", "uh", "like", "you know", "basically", "actually",
    "literally", "sort of", "kind of", "I mean", "right", "so",
]

SIMILARITY_THRESHOLD = 0.78


class AnalysisService:
    """Analyzes transcript segments for fillers, silence, and duplicates."""

    def __init__(self) -> None:
        self._similarity_model = None
        self._backend = None

    def _get_similarity_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._similarity_model is not None:
            return self._similarity_model

        try:
            from sentence_transformers import SentenceTransformer
            self._similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._backend = "sentence_transformers"
            logger.info("Loaded sentence-transformers model (all-MiniLM-L6-v2)")
        except ImportError:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                self._similarity_model = "tfidf"
                self._backend = "tfidf"
                logger.info("Using TF-IDF fallback for similarity")
            except ImportError:
                logger.warning("No similarity model available, skipping duplicate detection")
                self._similarity_model = "none"
                self._backend = "none"

        return self._similarity_model

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts (0.0 to 1.0)."""
        model = self._get_similarity_model()

        if self._backend == "sentence_transformers":
            from sentence_transformers import util
            emb1 = model.encode(text1, convert_to_tensor=True)
            emb2 = model.encode(text2, convert_to_tensor=True)
            score = util.cos_sim(emb1, emb2).item()
            return max(0.0, min(1.0, score))

        elif self._backend == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([text1, text2])
            score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return float(score)

        return 0.0

    def detect_fillers(
        self,
        segments: list[TranscriptSegment],
        filler_words: list[str] | None = None,
        silence_threshold_ms: int = 500,
    ) -> list[dict]:
        """Scan word_timestamps for filler words and silence gaps.

        Returns list of dicts describing filler/silence detections.
        """
        if filler_words is None:
            filler_words = DEFAULT_FILLER_WORDS

        filler_set = {fw.lower().strip() for fw in filler_words}
        results: list[dict] = []

        for segment in segments:
            word_ts = segment.word_timestamps
            if not word_ts or "words" not in word_ts:
                continue

            words = word_ts["words"]
            if not words:
                continue

            # Check for filler words
            filler_detected = False
            for word_info in words:
                word_text = word_info.get("word", "").lower().strip().rstrip(".,!?;:")
                if word_text in filler_set:
                    filler_detected = True
                    break

            # Multi-word fillers
            if not filler_detected:
                text_lower = segment.text.lower()
                for filler in filler_set:
                    if " " in filler and filler in text_lower:
                        filler_detected = True
                        break

            if filler_detected:
                results.append({
                    "segment_id": segment.id,
                    "updates": {
                        "segment_type": "filler",
                        "cut_decision": "cut",
                        "cut_reason": "filler word detected",
                    },
                })

            # Detect silence gaps
            silence_segments = self._detect_silence_gaps(segment, words, silence_threshold_ms)
            results.extend(silence_segments)

        return results

    def _detect_silence_gaps(
        self,
        segment: TranscriptSegment,
        words: list[dict],
        threshold_ms: int,
    ) -> list[dict]:
        """Find silence gaps between words within a segment."""
        silence_results: list[dict] = []

        for i in range(len(words) - 1):
            current_end = words[i].get("end_ms", 0)
            next_start = words[i + 1].get("start_ms", 0)
            gap_ms = next_start - current_end

            if gap_ms > threshold_ms:
                silence_results.append({
                    "new_segment": {
                        "clip_id": segment.clip_id,
                        "start_ms": current_end,
                        "end_ms": next_start,
                        "text": "[silence]",
                        "segment_type": "silence",
                        "cut_decision": "cut",
                        "cut_reason": f"silence gap {gap_ms}ms",
                        "confidence": 1.0,
                    },
                })

        return silence_results

    async def detect_repeated_takes(
        self,
        segments: list[TranscriptSegment],
        project_id: str,
    ) -> list[dict]:
        """Detect semantically similar consecutive passages using local embeddings.

        Uses sentence-transformers cosine similarity instead of Claude API.
        """
        model = self._get_similarity_model()
        if self._backend == "none":
            logger.warning("No similarity model available, skipping duplicate detection")
            return []

        if len(segments) < 2:
            return []

        speaker_groups = self._group_by_speaker(segments)
        results: list[dict] = []

        for group in speaker_groups:
            if len(group) < 2:
                continue
            duplicates = self._find_duplicates_in_group(group)
            results.extend(duplicates)

        return results

    def _group_by_speaker(
        self, segments: list[TranscriptSegment]
    ) -> list[list[TranscriptSegment]]:
        """Group consecutive segments by the same speaker."""
        if not segments:
            return []

        groups: list[list[TranscriptSegment]] = []
        current_group: list[TranscriptSegment] = [segments[0]]

        for seg in segments[1:]:
            if seg.speaker_id == current_group[-1].speaker_id:
                current_group.append(seg)
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [seg]

        if len(current_group) >= 2:
            groups.append(current_group)

        return groups

    def _find_duplicates_in_group(
        self,
        group: list[TranscriptSegment],
    ) -> list[dict]:
        """Find duplicate takes within a speaker group using embedding similarity."""
        results: list[dict] = []

        for i in range(len(group) - 1):
            p1 = group[i]
            p2 = group[i + 1]

            # Skip very short passages
            if len(p1.text.split()) < 5 or len(p2.text.split()) < 5:
                continue

            # Skip if more than 30 seconds apart (unlikely to be retakes)
            if p2.start_ms - p1.end_ms > 30000:
                continue

            similarity = self._compute_similarity(p1.text, p2.text)

            if similarity >= SIMILARITY_THRESHOLD:
                dup_group_id = str(uuid.uuid4())

                # Cut the first take, keep the last
                results.append({
                    "segment_id": p1.id,
                    "updates": {
                        "duplicate_group_id": dup_group_id,
                        "cut_decision": "cut",
                        "cut_reason": f"repeated take (similarity: {similarity:.0%})",
                        "quality_score": similarity,
                    },
                })

                results.append({
                    "segment_id": p2.id,
                    "updates": {
                        "duplicate_group_id": dup_group_id,
                        "quality_score": similarity,
                    },
                })

        return results

    async def detect_fillers_for_project(self, project_id: str) -> int:
        raise NotImplementedError("Use detect_fillers() with segments from the worker")

    async def detect_silence(self, project_id: str) -> int:
        raise NotImplementedError("Use detect_fillers() which includes silence detection")

    async def detect_duplicates(self, project_id: str) -> int:
        raise NotImplementedError("Use detect_repeated_takes() from the worker")

    async def analyze_project(self, project_id: str) -> dict:
        raise NotImplementedError("Use the task queue worker for full analysis")


# Module-level singleton
analysis_service = AnalysisService()
