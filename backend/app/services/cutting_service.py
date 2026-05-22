"""Service for computing cut decisions on transcript segments.

Responsibilities:
- Compute kept time ranges from segments
- Merge adjacent ranges within tolerance
- Respect user overrides (user_restored / user_cut)
"""

import logging

from app.models.segment import TranscriptSegment

logger = logging.getLogger(__name__)

# Merge ranges that are within this many ms of each other
MERGE_GAP_THRESHOLD_MS = 50


def compute_kept_ranges(segments: list[TranscriptSegment]) -> list[tuple[int, int]]:
    """Compute the list of kept time ranges from transcript segments.

    Takes a list of segments for a single clip and returns the time ranges
    that should be kept in the final output.

    Args:
        segments: List of TranscriptSegment instances for a single clip,
                  ordered by start_ms.

    Returns:
        List of (start_ms, end_ms) tuples for kept ranges, merged when
        adjacent ranges are within 50ms of each other.
    """
    # Filter to segments that should be kept
    kept_decisions = {"keep", "user_restored"}
    kept_segments = [
        seg for seg in segments
        if seg.cut_decision in kept_decisions
    ]

    if not kept_segments:
        return []

    # Sort by start time
    kept_segments.sort(key=lambda s: s.start_ms)

    # Build raw ranges
    raw_ranges: list[tuple[int, int]] = [
        (seg.start_ms, seg.end_ms) for seg in kept_segments
    ]

    # Merge adjacent ranges within threshold
    merged = _merge_ranges(raw_ranges, MERGE_GAP_THRESHOLD_MS)

    return merged


def _merge_ranges(
    ranges: list[tuple[int, int]], gap_threshold_ms: int
) -> list[tuple[int, int]]:
    """Merge time ranges that are within gap_threshold_ms of each other.

    Args:
        ranges: Sorted list of (start_ms, end_ms) tuples.
        gap_threshold_ms: Maximum gap between ranges to merge them.

    Returns:
        Merged list of (start_ms, end_ms) tuples.
    """
    if not ranges:
        return []

    merged: list[tuple[int, int]] = [ranges[0]]

    for start, end in ranges[1:]:
        prev_start, prev_end = merged[-1]

        # If this range starts within threshold of previous end, merge
        if start <= prev_end + gap_threshold_ms:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged


class CuttingService:
    """Computes which segments to cut and which to keep."""

    async def compute_cuts(self, project_id: str) -> dict:
        """Compute cut decisions for all segments in a project.

        Uses analysis results (filler, silence, duplicate markers) to decide
        which segments to cut. Does not override user-made decisions.

        Args:
            project_id: The project to process.

        Returns:
            Summary dict with counts of segments kept vs cut.
        """
        raise NotImplementedError(
            "Use compute_kept_ranges() directly from the worker/merge service"
        )

    async def select_best_take(self, duplicate_group_id: str) -> str:
        """From a group of duplicate takes, select the best one to keep.

        Uses quality_score and confidence to rank takes.

        Args:
            duplicate_group_id: UUID identifying the duplicate group.

        Returns:
            The segment ID of the best take.
        """
        raise NotImplementedError(
            "Best take selection is handled by the analysis_service during duplicate detection"
        )


# Module-level singleton
cutting_service = CuttingService()
