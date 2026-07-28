from enum import StrEnum


class RunStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    STALE = "stale"


class ProcessLiveness(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    FINISHED = "finished"
    MISSING = "missing"


class EventKind(StrEnum):
    LIFECYCLE = "lifecycle"
    PROVIDER = "provider"
    STDOUT = "stdout"
    STDERR = "stderr"
    VERIFICATION = "verification"
