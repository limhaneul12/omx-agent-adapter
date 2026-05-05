from enum import StrEnum


class CodexGoalExecutionShape(StrEnum):
    """Execution modes supported by the adapter-owned Codex Goal launch surface."""

    GOAL_ONLY = "goal_only"
    RALPH_PIPELINE = "ralph_pipeline"


class CodexGoalReviewPolicy(StrEnum):
    """Review policies that decide whether Ralph PRD handoff pauses for approval."""

    REVIEW_REQUIRED = "review_required"
    CONTINUE_AUTOMATICALLY = "continue_automatically"


class CodexGoalMirrorSource(StrEnum):
    """Sources that can produce adapter-owned Codex Goal mirror state."""

    CODEX_GOAL = "codex_goal"


class CodexGoalHandoffState(StrEnum):
    """Adapter-visible progress markers for Goal-to-Ralph handoff state."""

    GOAL_ONLY = "goal_only"
    AWAITING_RALPH = "awaiting_ralph"
    RALPH_STARTED = "ralph_started"
    UNKNOWN = "unknown"


class CodexGoalTrackingState(StrEnum):
    """Lifecycle states tracked by the adapter for a native Codex Goal session."""

    STARTING = "starting"
    ACTIVE = "active"
    ENDED = "ended"
    UNKNOWN = "unknown"


class CodexGoalSpawnStatus(StrEnum):
    """Native Codex Goal process spawn outcomes observed by the adapter."""

    STARTED = "started"
    FAILED = "failed"


class CodexGoalStatus(StrEnum):
    """Goal snapshot status values consumed by delegation selection."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    CLEARED = "cleared"
    UNKNOWN = "unknown"


class CodexGoalSource(StrEnum):
    """Goal snapshot producers visible to the supervisor layer."""

    CODEX_GOAL = "codex_goal"
    ADAPTER_SUPERVISOR = "adapter_supervisor"


class GoalDelegationTarget(StrEnum):
    """Delegation targets selected from a Codex Goal snapshot and operator state."""

    GOAL_ONLY = "goal_only"
    RALPH_PIPELINE = "ralph_pipeline"
    OBSERVE_ONLY = "observe_only"
    PLAIN_EXEC = "plain_exec"


class GoalDelegationDispatchStatus(StrEnum):
    """Dispatch outcomes for a selected Goal delegation target."""

    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"
    DISPATCHED = "dispatched"


class GoalDelegationDispatchAction(StrEnum):
    """Concrete runtime actions performed by Goal delegation dispatch."""

    NONE = "none"
    RALPH_LAUNCH = "ralph_launch"
    RALPH_RESUME = "ralph_resume"
    TEAM_LAUNCH = "team_launch"
