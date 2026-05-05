from enum import StrEnum


class UltraworkRuntimePhase(StrEnum):
    """Ultrawork runtime phase markers read from Ultrawork-owned state artifacts."""

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


class UltraworkRunOutcome(StrEnum):
    """Ultrawork run outcome markers used to classify launch/resume preflight state."""

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


class UltraworkStateClassification(StrEnum):
    """Adapter classifications for Ultrawork state preflight decisions."""

    CLEAN = "clean"
    RESUMABLE = "resumable"
    TERMINAL = "terminal"
    STALE = "stale"
    MISSING = "missing"
    INVALID = "invalid"
