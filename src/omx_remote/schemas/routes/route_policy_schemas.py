from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class RouteName(StrEnum):
    """Supported execution route names."""

    CODEX_EXEC = "codex_exec"
    CODEX_SUBAGENT = "codex_subagent"
    OMX_EXEC = "omx_exec"
    OMX_ULTRAGOAL = "omx_ultragoal"
    OMX_TEAM = "omx_team"
    OMX_RALPH = "omx_ralph"
    PROJECT_COMMAND = "project_command"
    PROMPT_ONLY = "prompt_only"
    LOCAL_VERIFY = "local_verify"
    MANUAL_HANDOFF = "manual_handoff"


class RouteTaskSize(StrEnum):
    """Normalized task size signals for route policy."""

    SMALL = "small"
    MEDIUM = "medium"
    ROADMAP = "roadmap"


class RouteTaskType(StrEnum):
    """Normalized task type signals for route policy."""

    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    RESEARCH = "research"
    PERFORMANCE = "performance"
    REFACTOR = "refactor"
    VERIFICATION = "verification"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class RouteRecommendationStatus(StrEnum):
    """Status of one route recommendation or alternative."""

    RECOMMENDED = "recommended"
    AVAILABLE = "available"
    BLOCKED = "blocked"


class RouteConfidence(StrEnum):
    """Confidence labels for route recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskClassification(StrictSchemaModel):
    """Represents deterministic task signals used by route policy."""

    task: NonEmptyString
    size: RouteTaskSize
    task_type: RouteTaskType
    needs_parallelism: bool = False
    needs_durable_state: bool = False
    signals: tuple[NonEmptyString, ...] = ()


class RouteRecommendation(StrictSchemaModel):
    """Represents one route recommendation or blocked alternative."""

    route: RouteName
    status: RouteRecommendationStatus
    confidence: RouteConfidence
    reason: NonEmptyString
    command_id: NonEmptyString | None = None
    blocked_by: tuple[NonEmptyString, ...] = ()


class RoutePolicyResult(StrictSchemaModel):
    """Represents a route policy decision for one task."""

    task: NonEmptyString
    classification: TaskClassification
    recommendations: tuple[RouteRecommendation, ...]
    blocked_alternatives: tuple[RouteRecommendation, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class RouteExplanation(StrictSchemaModel):
    """Represents human/agent explanation metadata for one route."""

    route: RouteName
    summary: NonEmptyString
    typical_use: NonEmptyString
    preflight_route: NonEmptyString | None = None
