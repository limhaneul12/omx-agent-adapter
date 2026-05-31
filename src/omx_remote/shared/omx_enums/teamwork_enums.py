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
