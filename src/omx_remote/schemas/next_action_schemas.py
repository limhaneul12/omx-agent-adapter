from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.route_policy_schemas import RouteRecommendation


class NextActionRequest(StrictSchemaModel):
    """Request boundary for read-only next-action recommendation."""

    repo_root: NonEmptyString
    task: NonEmptyString | None = None
    team_names: tuple[NonEmptyString, ...] = ()


class NextActionResult(StrictSchemaModel):
    """Read-only recommendation for the next safe repository action."""

    recommended_action: NonEmptyString
    safe_to_mutate: bool
    requires_review: bool
    summary: NonEmptyString
    why: tuple[NonEmptyString, ...]
    source_names: tuple[NonEmptyString, ...]
    recommended_commands: tuple[NonEmptyString, ...] = ()
    blocked_actions: tuple[NonEmptyString, ...] = ()
    route_recommendations: tuple[RouteRecommendation, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()
