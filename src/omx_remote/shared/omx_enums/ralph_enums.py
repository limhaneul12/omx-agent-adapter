from enum import StrEnum


class RalphRuntimePhase(StrEnum):
    """Ralph runtime phase markers read from Ralph-owned state artifacts."""

    STARTING = "starting"
    RUNNING = "running"
    EXECUTING = "executing"
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    IDLE = "idle"
    USER_INTERLUDE = "userinterlude"
    BLOCKED_ON_USER = "blocked_on_user"
    WAITING = "waiting"
    COMPLETE = "complete"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RalphRunOutcome(StrEnum):
    """Ralph run outcome markers used to classify resumable and terminal state."""

    FINISH = "finish"
    BLOCKED_ON_USER = "blocked_on_user"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETE = "complete"
    COMPLETED = "completed"
    DONE = "done"
    USER_INTERLUDE = "userinterlude"
    CONTINUE = "continue"
    PROGRESS = "progress"
    RUNNING = "running"
    ACTIVE = "active"


class RalphPrdContinuationPolicy(StrEnum):
    """Ralph PRD follow-up policies after a PRD artifact is produced."""

    REVIEW_REQUIRED = "review_required"
    CONTINUE_AUTOMATICALLY = "continue_automatically"


class TeamWorkerAuthorizationPolicy(StrEnum):
    """Per-worker authorization policies for Team assignment allow decisions."""

    HUMAN_REQUIRED = "human_required"
    LLM_REVIEW = "llm_review"
    PREAPPROVED = "preapproved"


class TeamAdminAggregationPolicy(StrEnum):
    """Team Admin worker-result collection policies owned by Ralph PRDs."""

    COLLECT_ALL_WORKERS_THEN_REVIEW = "collect_all_workers_then_review"


class TeamAdminMergePolicy(StrEnum):
    """Team Admin merge-readiness policies owned by Ralph PRDs."""

    REVIEW_BEFORE_MERGE = "review_before_merge"


class TeamAdminCompletionPolicy(StrEnum):
    """Team Admin completion policies checked before Ralph post-Team review."""

    ALL_REQUIRED_TASKS_COMPLETED = "all_required_tasks_completed"


class RalphStateClassification(StrEnum):
    """Adapter classifications for Ralph state preflight decisions."""

    CLEAN = "clean"
    RESUMABLE = "resumable"
    TERMINAL = "terminal"
    STALE = "stale"
    MISSING = "missing"
    INVALID = "invalid"
