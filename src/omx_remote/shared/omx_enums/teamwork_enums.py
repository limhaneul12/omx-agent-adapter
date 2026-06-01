from enum import StrEnum


class TeamProofLayerName(StrEnum):
    """Stable proof-layer names for Team launch/status evidence."""

    PRD_DAG_IMPORT = "prd_dag_import"
    ASSIGNMENT = "assignment"
    WORKER_READINESS = "worker_readiness"
    DISPATCH = "dispatch"
    COMPLETION = "completion"


class TeamProofLayerState(StrEnum):
    """Machine-readable state for one Team proof layer."""

    MISSING = "missing"
    PARTIAL = "partial"
    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class TeamCompletedTaskState(StrEnum):
    """Task states that count as completed Team output."""

    COMPLETE = "complete"
    COMPLETED = "completed"
    DONE = "done"
    SUCCESS = "success"
    SUCCEEDED = "succeeded"


class TeamBlockedTaskState(StrEnum):
    """Task states that count as blocked Team output."""

    BLOCKED = "blocked"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"
    DEAD = "dead"


class TeamBlockedWorkerState(StrEnum):
    """Worker states that count as blocked Team execution."""

    BLOCKED = "blocked"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"
    DEAD = "dead"


class TeamStartupIssueWorkerState(StrEnum):
    """Worker states that indicate Team startup readiness issues."""

    READY_PROMPT_TIMEOUT = "ready_prompt_timeout"
    STARTUP_PROMPT_TIMEOUT = "startup_prompt_timeout"
    STARTUP_TIMEOUT = "startup_timeout"
    WORKER_STARTUP_TIMEOUT = "worker_startup_timeout"


class TeamStartupIssueEventType(StrEnum):
    """Event types that indicate Team startup readiness issues."""

    READY_PROMPT_TIMEOUT = "ready_prompt_timeout"
    STARTUP_PROMPT_TIMEOUT = "startup_prompt_timeout"
    WORKER_STARTUP_TIMEOUT = "worker_startup_timeout"


COMPLETED_TASK_STATE_VALUES: frozenset[str] = frozenset(
    state.value for state in TeamCompletedTaskState
)
BLOCKED_TASK_STATE_VALUES: frozenset[str] = frozenset(
    state.value for state in TeamBlockedTaskState
)
BLOCKED_WORKER_STATE_VALUES: frozenset[str] = frozenset(
    state.value for state in TeamBlockedWorkerState
)
STARTUP_ISSUE_WORKER_STATE_VALUES: frozenset[str] = frozenset(
    state.value for state in TeamStartupIssueWorkerState
)
STARTUP_ISSUE_EVENT_TYPE_VALUES: frozenset[str] = frozenset(
    state.value for state in TeamStartupIssueEventType
)


class TeamOperatorDispatchOperation(StrEnum):
    """Low-level Team operation selected by the operator facade."""

    SEND_MESSAGE = "send-message"
    WRITE_WORKER_INBOX = "write-worker-inbox"
    BROADCAST = "broadcast"
    CREATE_TASK = "create-task"
    WRITE_TASK_APPROVAL = "write-task-approval"


class TeamOperatorDispatchOutcomeState(StrEnum):
    """Outcome states returned by Team operator dispatch operations."""

    ACCEPTED = "accepted"
    ACCEPTED_BUT_UNVERIFIED = "accepted_but_unverified"
    FAILED = "failed"


class TeamOperatorDeliveryMode(StrEnum):
    """Worker follow-up delivery modes selected by the Team operator facade."""

    DIRECT_MESSAGE = "direct_message"
    DURABLE_INBOX = "durable_inbox"
