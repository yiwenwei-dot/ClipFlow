"""Service for computing cut decisions on transcript segments.

Responsibilities:
- Apply automatic cut decisions based on analysis results
- Handle filler word removal decisions
- Handle silence trimming decisions
- Select best take from duplicate groups
- Respect user overrides (user_restored / user_cut)
"""


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
        raise NotImplementedError

    async def select_best_take(self, duplicate_group_id: str) -> str:
        """From a group of duplicate takes, select the best one to keep.

        Uses quality_score and confidence to rank takes.

        Args:
            duplicate_group_id: UUID identifying the duplicate group.

        Returns:
            The segment ID of the best take.
        """
        raise NotImplementedError
