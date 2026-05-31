from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.route_enums import (
    RouteConfidence,
    RouteName,
    RouteRecommendationStatus,
    RouteTaskSize,
    RouteTaskType,
)


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
