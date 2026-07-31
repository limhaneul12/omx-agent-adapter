from enum import StrEnum


class CapabilitySupport(StrEnum):
    SUPPORTED = "supported"
    CONDITIONAL = "conditional"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class NativeCapability(StrEnum):
    DETACHED_EXECUTION = "detached_execution"
    CANCELLATION = "cancellation"
    RESUME = "resume"
    INTERACTIVE_INPUT = "interactive_input"
    STRUCTURED_EVENTS = "structured_events"
    STRUCTURED_SUBAGENTS = "structured_subagents"
    ARTIFACTS = "artifacts"
    NATIVE_TEAM = "native_team"
    NATIVE_LOOP = "native_loop"
    PARALLEL_WORKERS = "parallel_workers"


class StrategyNodeType(StrEnum):
    NATIVE_RUN = "native_run"
    NATIVE_RESUME = "native_resume"
    HANDOFF = "handoff"
    VALIDATOR = "validator"
    FINISH = "finish"


class StrategyStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StrategyStageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StrategyFailureAction(StrEnum):
    STOP = "stop"
    CONTINUE = "continue"


class StrategyRunCondition(StrEnum):
    ALL_DEPENDENCIES_SUCCEEDED = "all_dependencies_succeeded"
    ANY_DEPENDENCY_SUCCEEDED = "any_dependency_succeeded"
    ANY_DEPENDENCY_FAILED = "any_dependency_failed"


class StrategyValidatorKind(StrEnum):
    RUN_EVIDENCE = "run_evidence"
    ARTIFACT_PRESENCE = "artifact_presence"
    BLOCKER_COUNT = "blocker_count"


class StrategyEventKind(StrEnum):
    STRATEGY = "strategy"
    STAGE = "stage"
    EVIDENCE = "evidence"
