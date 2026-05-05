from enum import StrEnum


class OperatorLoopState(StrEnum):
    """Stable loop states returned by adapter-owned operator actions."""

    SUCCESS = "success"
    RESUMABLE_LATER = "resumable_later"
    RETRYABLE_AFTER_CLEANUP = "retryable_after_cleanup"
    BLOCKED_APPROVAL_NEEDED = "blocked_approval_needed"
    TERMINAL_FAILURE = "terminal_failure"
    STALE_STATE_FAILURE = "stale_state_failure"
    DIRTY_WORKSPACE_FAILURE = "dirty_workspace_failure"
    NO_RESUMABLE_STATE_FAILURE = "no_resumable_state_failure"


class OperatorNextAction(StrEnum):
    """Next recommended control actions after an operator loop result."""

    OBSERVE = "observe"
    LAUNCH = "launch"
    RESUME = "resume"
    RETRY = "retry"
    CANCEL = "cancel"
    CLEANUP = "cleanup"
    ESCALATE = "escalate"
    NONE = "none"


class OperatorLane(StrEnum):
    """Operator lanes that can be controlled through the adapter action surface."""

    RALPH = "ralph"
    ULTRAWORK = "ultrawork"
    TEAM = "team"
