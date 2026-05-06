from enum import StrEnum


class TeamAdminAggregationState(StrEnum):
    """Stable Team Admin final aggregation states for Ralph review handoff."""

    READY_FOR_RALPH_REVIEW = "ready_for_ralph_review"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    WAITING_FOR_WORKERS = "waiting_for_workers"
