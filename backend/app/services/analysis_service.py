"""Service for AI-powered content analysis.

Responsibilities:
- Detect filler words in transcript segments
- Identify silence gaps between words
- Find repeated takes / duplicate content using Claude API
- Assign quality scores to segments
"""

import logging
import uuid

import anthropic

from app.config import settings
from app.models.segment import TranscriptSegment

logger = logging.getLogger(__name__)

DEFAULT_FILLER_WORDS = [
    "um", "uh", "like", "you know", "basically", "actually",
    "literally", "sort of", "kind of", "I mean", "right", "so",
]


class AnalysisService:
    """Analyzes transcript segments for fillers, silence, and duplicates."""

    def __init__(self) -> None:
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY

    def detect_fillers(
        self,
        segments: list[TranscriptSegment],
        filler_words: list[str] | None = None,
        silence_threshold_ms: int = 500,
    ) -> list[dict]:
        """Scan word_timestamps in segments for filler words and silence gaps.

        Args:
            segments: List of TranscriptSegment model instances.
            filler_words: List of filler word strings to detect.
            silence_threshold_ms: Gap between words in ms that counts as silence.

        Returns:
            List of dicts describing filler/silence detections with segment updates.
            Each dict has: segment_id, updates (dict of field changes),
            or new_segments (list of new sub-segments to create).
        """
        if filler_words is None:
            filler_words = DEFAULT_FILLER_WORDS

        # Normalize filler words for matching
        filler_set = {fw.lower().strip() for fw in filler_words}
        results: list[dict] = []

        for segment in segments:
            word_ts = segment.word_timestamps
            if not word_ts or "words" not in word_ts:
                continue

            words = word_ts["words"]
            if not words:
                continue

            # Check for filler words in this segment's word timestamps
            filler_detected = False
            for word_info in words:
                word_text = word_info.get("word", "").lower().strip().rstrip(".,!?;:")
                if word_text in filler_set:
                    filler_detected = True
                    break

            # Check for multi-word fillers (e.g., "you know", "sort of")
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

            # Detect silence gaps between words within this segment
            silence_segments = self._detect_silence_gaps(segment, words, silence_threshold_ms)
            results.extend(silence_segments)

        return results

    def _detect_silence_gaps(
        self,
        segment: TranscriptSegment,
        words: list[dict],
        threshold_ms: int,
    ) -> list[dict]:
        """Find silence gaps between words within a segment.

        Returns list of new silence sub-segment definitions.
        """
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
        """Detect semantically similar consecutive passages using Claude API.

        Groups consecutive segments by speaker, then uses Claude to identify
        repeated takes (where the speaker says essentially the same thing twice).

        Args:
            segments: List of TranscriptSegment instances, ordered by time.
            project_id: The project ID.

        Returns:
            List of dicts with segment_id and updates for duplicate detection.
        """
        if not self.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping duplicate detection")
            return []

        if len(segments) < 2:
            return []

        # Group consecutive segments by speaker
        speaker_groups = self._group_by_speaker(segments)
        results: list[dict] = []

        try:
            client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)

            for group in speaker_groups:
                if len(group) < 2:
                    continue

                # Compare consecutive passages within the speaker group
                duplicates = await self._find_duplicates_in_group(client, group)
                results.extend(duplicates)

        except anthropic.APIError as e:
            logger.error("Anthropic API error during duplicate detection: %s", str(e))
        except Exception:
            logger.exception("Unexpected error during duplicate detection")

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

    async def _find_duplicates_in_group(
        self,
        client: anthropic.AsyncAnthropic,
        group: list[TranscriptSegment],
    ) -> list[dict]:
        """Use Claude to detect semantically similar passages in a speaker group."""
        results: list[dict] = []

        # Build passage pairs to compare
        passages = []
        for seg in group:
            passages.append({"id": seg.id, "text": seg.text, "segment": seg})

        # Compare consecutive passages
        for i in range(len(passages) - 1):
            p1 = passages[i]
            p2 = passages[i + 1]

            # Skip very short passages
            if len(p1["text"].split()) < 5 or len(p2["text"].split()) < 5:
                continue

            is_duplicate = await self._compare_passages(client, p1["text"], p2["text"])

            if is_duplicate:
                dup_group_id = str(uuid.uuid4())

                # Mark the first one as cut (keep the LAST take)
                results.append({
                    "segment_id": p1["id"],
                    "updates": {
                        "duplicate_group_id": dup_group_id,
                        "cut_decision": "cut",
                        "cut_reason": "repeated take",
                    },
                })

                # Mark the second one as kept duplicate
                results.append({
                    "segment_id": p2["id"],
                    "updates": {
                        "duplicate_group_id": dup_group_id,
                        # Keep the last take
                    },
                })

        return results

    async def _compare_passages(
        self, client: anthropic.AsyncAnthropic, text1: str, text2: str
    ) -> bool:
        """Ask Claude if two passages express the same idea (repeated take)."""
        prompt = (
            "You are analyzing video transcript segments to detect repeated takes. "
            "A repeated take is when a speaker says essentially the same thing twice, "
            "as if they are re-recording or re-stating the same point.\n\n"
            f"Passage 1: \"{text1}\"\n\n"
            f"Passage 2: \"{text2}\"\n\n"
            "Do these two passages express the same core idea, as if the speaker "
            "is taking another attempt at saying the same thing? "
            "Answer ONLY 'yes' or 'no'."
        )

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )

            answer = response.content[0].text.strip().lower()
            return answer.startswith("yes")

        except Exception:
            logger.exception("Error comparing passages with Claude")
            return False

    async def detect_fillers_for_project(
        self, project_id: str
    ) -> int:
        """Scan segments for filler words and mark them.

        This is a convenience alias used by older code paths.
        The actual logic runs via detect_fillers() with segments passed in.

        Args:
            project_id: The project to analyze.

        Returns:
            Number of filler segments detected.
        """
        raise NotImplementedError("Use detect_fillers() with segments from the worker")

    async def detect_silence(self, project_id: str) -> int:
        """Identify silence gaps exceeding the project threshold.

        Args:
            project_id: The project to analyze.

        Returns:
            Number of silence segments created.
        """
        raise NotImplementedError("Use detect_fillers() which includes silence detection")

    async def detect_duplicates(self, project_id: str) -> int:
        """Use Claude API to find repeated takes of the same content.

        Args:
            project_id: The project to analyze.

        Returns:
            Number of duplicate groups found.
        """
        raise NotImplementedError("Use detect_repeated_takes() from the worker")

    async def analyze_project(self, project_id: str) -> dict:
        """Run full analysis pipeline on a project.

        Args:
            project_id: The project to analyze.

        Returns:
            Summary dict with counts of each detection type.
        """
        raise NotImplementedError("Use the task queue worker for full analysis")


# Module-level singleton
analysis_service = AnalysisService()
