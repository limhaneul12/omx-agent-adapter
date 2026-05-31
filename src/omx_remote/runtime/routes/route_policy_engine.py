from pathlib import Path

from omx_remote.runtime.cockpit.sources.agent_config import (
    summarize_cockpit_agent_config,
)
from omx_remote.runtime.cockpit.sources.capability_snapshot import (
    read_cockpit_capabilities,
)
from omx_remote.runtime.cockpit.sources.command_recipes import (
    summarize_cockpit_command_recipes,
)
from omx_remote.runtime.routes.task_signal_classifier import classify_task_signals
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
    CockpitCapabilitiesSnapshot,
    CockpitCommandRecipeSummary,
    CockpitRuntimeCapability,
)
from omx_remote.schemas.routes.route_policy_schemas import (
    RouteConfidence,
    RouteName,
    RoutePolicyResult,
    RouteRecommendation,
    RouteRecommendationStatus,
    RouteTaskSize,
    RouteTaskType,
    TaskClassification,
)


def _runtime_command_available(
    runtime: CockpitRuntimeCapability,
    command_name: str,
) -> bool:
    """Return whether a runtime exposes a named command capability.

    Args:
        runtime [CockpitRuntimeCapability]: Runtime capability snapshot.
        command_name [str]: Command capability name to search for.

    Returns:
        bool: ``True`` when the command is present and available.
    """
    command_available: bool = any(
        command.name == command_name and command.available
        for command in runtime.commands
    )
    return command_available


def _recipe_available(recipe_summary: CockpitCommandRecipeSummary, qualified_id: str) -> bool:
    """Return whether a command recipe is available.

    Args:
        recipe_summary [CockpitCommandRecipeSummary]: Command recipe summary.
        qualified_id [str]: Source-qualified command id to find.

    Returns:
        bool: ``True`` when the recipe id is present.
    """
    recipe_available: bool = qualified_id in recipe_summary.qualified_ids
    return recipe_available


def _route_blockers(
    route: RouteName,
    capabilities: CockpitCapabilitiesSnapshot,
    safe_to_mutate: bool,
    active_runtime_modes: tuple[str, ...],
) -> tuple[str, ...]:
    """Build blockers for one route.

    Args:
        route [RouteName]: Route to evaluate.
        capabilities [CockpitCapabilitiesSnapshot]: Native capability snapshot.
        safe_to_mutate [bool]: Whether cockpit evidence says mutation is safe.
        active_runtime_modes [tuple[str, ...]]: Active runtime mode names.

    Returns:
        tuple[str, ...]: Human-readable route blockers.
    """
    blockers: list[str] = []
    if route in {RouteName.CODEX_EXEC, RouteName.CODEX_SUBAGENT} and not capabilities.codex.available:
        blockers.append("codex executable is unavailable")
    if route in {RouteName.OMX_EXEC, RouteName.OMX_ULTRAGOAL, RouteName.OMX_TEAM, RouteName.OMX_RALPH} and not capabilities.omx.available:
        blockers.append("omx executable is unavailable")
    if route == RouteName.OMX_ULTRAGOAL and not _runtime_command_available(
        capabilities.omx,
        "ultragoal",
    ):
        blockers.append("omx ultragoal command is unavailable")
    if route == RouteName.OMX_TEAM and not _runtime_command_available(
        capabilities.omx,
        "team",
    ):
        blockers.append("omx team command is unavailable")
    if route == RouteName.OMX_TEAM and active_runtime_modes:
        blockers.append(f"active runtime modes: {', '.join(active_runtime_modes)}")
    elif route == RouteName.OMX_TEAM and not safe_to_mutate:
        blockers.append("cockpit evidence says mutation is not safe")

    route_blockers: tuple[str, ...] = tuple(blockers)
    return route_blockers


def _recommend_project_command(
    recipe_summary: CockpitCommandRecipeSummary,
    command_id: str,
    reason: str,
) -> RouteRecommendation | None:
    """Build a project-command recommendation when a recipe exists.

    Args:
        recipe_summary [CockpitCommandRecipeSummary]: Command recipe summary.
        command_id [str]: Source-qualified command id.
        reason [str]: Recommendation reason.

    Returns:
        RouteRecommendation | None: Recommendation when available.
    """
    if not _recipe_available(recipe_summary, command_id):
        missing_recommendation: None = None
        return missing_recommendation

    recommendation = RouteRecommendation(
        route=RouteName.PROJECT_COMMAND,
        status=RouteRecommendationStatus.RECOMMENDED,
        confidence=RouteConfidence.HIGH,
        reason=reason,
        command_id=command_id,
    )
    return recommendation


def _blocked_recommendation(
    route: RouteName,
    blockers: tuple[str, ...],
    reason: str,
) -> RouteRecommendation:
    """Build a blocked route alternative.

    Args:
        route [RouteName]: Blocked route.
        blockers [tuple[str, ...]]: Blocker details.
        reason [str]: Route-specific explanation.

    Returns:
        RouteRecommendation: Blocked route alternative.
    """
    blocked = RouteRecommendation(
        route=route,
        status=RouteRecommendationStatus.BLOCKED,
        confidence=RouteConfidence.LOW,
        reason=reason,
        blocked_by=blockers,
    )
    return blocked


def _append_route_if_available(
    recommendations: list[RouteRecommendation],
    blocked: list[RouteRecommendation],
    route: RouteName,
    capabilities: CockpitCapabilitiesSnapshot,
    safe_to_mutate: bool,
    active_runtime_modes: tuple[str, ...],
    confidence: RouteConfidence,
    reason: str,
) -> None:
    """Append an available recommendation or blocked alternative.

    Args:
        recommendations [list[RouteRecommendation]]: Mutable recommendation list.
        blocked [list[RouteRecommendation]]: Mutable blocked alternatives list.
        route [RouteName]: Route to evaluate.
        capabilities [CockpitCapabilitiesSnapshot]: Native capability snapshot.
        safe_to_mutate [bool]: Whether mutation is safe.
        active_runtime_modes [tuple[str, ...]]: Active runtime mode names.
        confidence [RouteConfidence]: Recommendation confidence.
        reason [str]: Recommendation reason.
    """
    blockers: tuple[str, ...] = _route_blockers(
        route,
        capabilities,
        safe_to_mutate,
        active_runtime_modes,
    )
    if blockers:
        blocked.append(_blocked_recommendation(route, blockers, reason))
        return

    recommendation = RouteRecommendation(
        route=route,
        status=RouteRecommendationStatus.RECOMMENDED,
        confidence=confidence,
        reason=reason,
    )
    recommendations.append(recommendation)


def _build_recommendations(
    classification: TaskClassification,
    capabilities: CockpitCapabilitiesSnapshot,
    agent_summary: CockpitAgentConfigSummary,
    recipe_summary: CockpitCommandRecipeSummary,
    safe_to_mutate: bool,
    active_runtime_modes: tuple[str, ...],
) -> tuple[tuple[RouteRecommendation, ...], tuple[RouteRecommendation, ...]]:
    """Build route recommendations and blocked alternatives.

    Args:
        classification [TaskClassification]: Classified task signals.
        capabilities [CockpitCapabilitiesSnapshot]: Native capability snapshot.
        agent_summary [CockpitAgentConfigSummary]: Configured agent summary.
        recipe_summary [CockpitCommandRecipeSummary]: Command recipe summary.
        safe_to_mutate [bool]: Whether mutation is safe.
        active_runtime_modes [tuple[str, ...]]: Active runtime mode names.

    Returns:
        tuple[tuple[RouteRecommendation, ...], tuple[RouteRecommendation, ...]]: Recommendations and blocked alternatives.
    """
    recommendations: list[RouteRecommendation] = []
    blocked: list[RouteRecommendation] = []
    if classification.task_type == RouteTaskType.REVIEW:
        project_review = _recommend_project_command(
            recipe_summary,
            "builtin:review-diff",
            "The task is a review and the built-in diff review recipe is available.",
        )
        if project_review is not None:
            recommendations.append(project_review)
    elif classification.task_type == RouteTaskType.VERIFICATION:
        project_verify = _recommend_project_command(
            recipe_summary,
            "builtin:verify-handoff-plus",
            "The task is verification and the built-in handoff verification recipe is available.",
        )
        if project_verify is not None:
            recommendations.append(project_verify)
    elif classification.size == RouteTaskSize.ROADMAP or classification.needs_durable_state:
        _append_route_if_available(
            recommendations,
            blocked,
            RouteName.OMX_ULTRAGOAL,
            capabilities,
            safe_to_mutate,
            active_runtime_modes,
            RouteConfidence.HIGH,
            "The task needs durable multi-goal state, and native UltraGoal is the strongest route when available.",
        )
    elif classification.needs_parallelism:
        if agent_summary.enabled_count > 0 and capabilities.codex.available:
            recommendations.append(
                RouteRecommendation(
                    route=RouteName.CODEX_SUBAGENT,
                    status=RouteRecommendationStatus.RECOMMENDED,
                    confidence=RouteConfidence.MEDIUM,
                    reason="The task asks for parallel work and enabled TOML agents are configured.",
                )
            )
        _append_route_if_available(
            recommendations,
            blocked,
            RouteName.OMX_TEAM,
            capabilities,
            safe_to_mutate,
            active_runtime_modes,
            RouteConfidence.MEDIUM,
            "The task asks for worker fanout, so OMX Team is a candidate when the runtime is healthy.",
        )

    if not recommendations:
        _append_route_if_available(
            recommendations,
            blocked,
            RouteName.CODEX_EXEC,
            capabilities,
            safe_to_mutate,
            active_runtime_modes,
            RouteConfidence.MEDIUM,
            "Default to a direct Codex execution route for scoped work.",
        )

    team_blockers: tuple[str, ...] = _route_blockers(
        RouteName.OMX_TEAM,
        capabilities,
        safe_to_mutate,
        active_runtime_modes,
    )
    if team_blockers and all(alternative.route != RouteName.OMX_TEAM for alternative in blocked):
        blocked.append(
            _blocked_recommendation(
                RouteName.OMX_TEAM,
                team_blockers,
                "OMX Team is not currently safe for fanout.",
            )
        )

    result: tuple[tuple[RouteRecommendation, ...], tuple[RouteRecommendation, ...]] = (
        tuple(recommendations),
        tuple(blocked),
    )
    return result


def build_route_policy_result(
    task: str,
    cwd: str | Path,
    capabilities: CockpitCapabilitiesSnapshot | None = None,
    agent_summary: CockpitAgentConfigSummary | None = None,
    recipe_summary: CockpitCommandRecipeSummary | None = None,
    safe_to_mutate: bool = True,
    active_runtime_modes: tuple[str, ...] = (),
) -> RoutePolicyResult:
    """Build an explainable route policy result.

    Args:
        task [str]: Task text to classify.
        cwd [str | Path]: Repository root used to load local config.
        capabilities [CockpitCapabilitiesSnapshot | None]: Optional pre-read capability snapshot.
        agent_summary [CockpitAgentConfigSummary | None]: Optional pre-read agent summary.
        recipe_summary [CockpitCommandRecipeSummary | None]: Optional pre-read command recipe summary.
        safe_to_mutate [bool]: Whether current cockpit evidence permits mutation.
        active_runtime_modes [tuple[str, ...]]: Active runtime mode names.

    Returns:
        RoutePolicyResult: Deterministic route policy result.
    """
    resolved_capabilities: CockpitCapabilitiesSnapshot = (
        read_cockpit_capabilities() if capabilities is None else capabilities
    )
    resolved_agent_summary: CockpitAgentConfigSummary = (
        summarize_cockpit_agent_config(cwd) if agent_summary is None else agent_summary
    )
    resolved_recipe_summary: CockpitCommandRecipeSummary = (
        summarize_cockpit_command_recipes(cwd) if recipe_summary is None else recipe_summary
    )
    classification: TaskClassification = classify_task_signals(task)
    recommendations, blocked = _build_recommendations(
        classification=classification,
        capabilities=resolved_capabilities,
        agent_summary=resolved_agent_summary,
        recipe_summary=resolved_recipe_summary,
        safe_to_mutate=safe_to_mutate,
        active_runtime_modes=active_runtime_modes,
    )
    warnings: tuple[str, ...] = (
        *resolved_capabilities.codex.warnings,
        *resolved_capabilities.omx.warnings,
        *resolved_agent_summary.warnings,
        *resolved_recipe_summary.warnings,
    )
    result = RoutePolicyResult(
        task=task,
        classification=classification,
        recommendations=recommendations,
        blocked_alternatives=blocked,
        warnings=warnings,
    )
    return result
