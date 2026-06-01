from omx_remote.runtime.cockpit.snapshot.decisions import (
    _build_decision_reasons,
    _build_runtime_contradictions,
    _derive_recommended_next_action,
    _derive_safe_to_mutate,
)
from omx_remote.runtime.cockpit.snapshot.lanes import _build_lane_snapshots
from omx_remote.runtime.routes.route_policy_engine import build_route_policy_result
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
    CockpitCapabilitiesSnapshot,
    CockpitCommandRecipeSummary,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitContradiction,
    CockpitDecisionReason,
    CockpitLaneSnapshot,
    CockpitPullRequestObservation,
    CockpitSnapshot,
    CockpitStatusSourceObservation,
    CockpitTeamObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.route_policy_schemas import RouteRecommendation
from omx_remote.schemas.runtime_status_schemas import ActiveRuntimeModes, RuntimeStatus
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification


def build_cockpit_snapshot(
    repo_root: str,
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    goal_mirror_state: CodexGoalMirrorState | None,
    ultrawork_state_classification: UltraworkStateClassification,
    ultrawork_warnings: tuple[str, ...],
    team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...] = (),
    discovered_team_names: tuple[str, ...] = (),
    status_sources: tuple[CockpitStatusSourceObservation, ...] = (),
    pull_request_status: CockpitPullRequestObservation | None = None,
    capabilities: CockpitCapabilitiesSnapshot | None = None,
    configured_agents: CockpitAgentConfigSummary | None = None,
    command_recipes: CockpitCommandRecipeSummary | None = None,
    route_recommendations: tuple[RouteRecommendation, ...] = (),
    blocked_route_alternatives: tuple[RouteRecommendation, ...] = (),
    warnings: tuple[str, ...] = (),
) -> CockpitSnapshot:
    """Build a read-only cockpit snapshot from normalized surface observations.

    Args:
        repo_root [str]: Workspace root being summarized.
        runtime_status [RuntimeStatus]: Normalized `omx status` snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Normalized active mode list.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional adapter-owned Goal mirror state.
        ultrawork_state_classification [UltraworkStateClassification]: Ultrawork state classification.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork status warnings.
        team_names [tuple[str, ...]]: Explicit Team names included in this cockpit read.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.
        discovered_team_names [tuple[str, ...]]: Exact Team names discovered from durable artifacts.
        status_sources [tuple[CockpitStatusSourceObservation, ...]]: Source observations read by the cockpit.
        pull_request_status [CockpitPullRequestObservation | None]: Optional PR/review/check evidence.
        capabilities [CockpitCapabilitiesSnapshot | None]: Optional native capability snapshot.
        configured_agents [CockpitAgentConfigSummary | None]: Optional configured-agent summary.
        command_recipes [CockpitCommandRecipeSummary | None]: Optional command recipe summary.
        route_recommendations [tuple[RouteRecommendation, ...]]: Optional route recommendations.
        blocked_route_alternatives [tuple[RouteRecommendation, ...]]: Optional blocked route alternatives.
        warnings [tuple[str, ...]]: Top-level degraded evidence warnings.

    Returns:
        CockpitSnapshot: Aggregated cockpit snapshot with lane states and top-level guidance.
    """
    contradictions: tuple[CockpitContradiction, ...] = _build_runtime_contradictions(
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
    )
    lanes: tuple[CockpitLaneSnapshot, ...] = _build_lane_snapshots(
        repo_root=repo_root,
        goal_mirror_state=goal_mirror_state,
        ultrawork_state_classification=ultrawork_state_classification,
        ultrawork_warnings=ultrawork_warnings,
        team_names=team_names,
        team_observations=team_observations,
    )
    safe_to_mutate: bool = _derive_safe_to_mutate(
        contradictions=contradictions,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
        team_observations=team_observations,
    )
    recommended_next_action: str = _derive_recommended_next_action(
        contradictions=contradictions,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
        goal_mirror_state=goal_mirror_state,
        team_observations=team_observations,
    )
    decision_reasons: tuple[CockpitDecisionReason, ...] = _build_decision_reasons(
        contradictions=contradictions,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
        goal_mirror_state=goal_mirror_state,
        team_observations=team_observations,
    )
    resolved_route_recommendations: tuple[RouteRecommendation, ...] = (
        route_recommendations
    )
    resolved_blocked_route_alternatives: tuple[RouteRecommendation, ...] = (
        blocked_route_alternatives
    )
    if (
        capabilities is not None
        and configured_agents is not None
        and command_recipes is not None
        and not route_recommendations
    ):
        route_policy = build_route_policy_result(
            task="execute a durable multi-goal roadmap",
            cwd=repo_root,
            capabilities=capabilities,
            agent_summary=configured_agents,
            recipe_summary=command_recipes,
            safe_to_mutate=safe_to_mutate,
            active_runtime_modes=active_runtime_modes.active_modes,
        )
        resolved_route_recommendations = route_policy.recommendations
        resolved_blocked_route_alternatives = route_policy.blocked_alternatives
    result: CockpitSnapshot = CockpitSnapshot(
        repo_root=repo_root,
        runtime_summary=runtime_status.summary,
        active_runtime_modes=active_runtime_modes.active_modes,
        discovered_teams=discovered_team_names,
        status_sources=status_sources,
        pull_request_status=pull_request_status,
        capabilities=capabilities,
        configured_agents=configured_agents,
        command_recipes=command_recipes,
        route_recommendations=resolved_route_recommendations,
        blocked_route_alternatives=resolved_blocked_route_alternatives,
        contradictions=contradictions,
        lanes=lanes,
        warnings=warnings,
        safe_to_mutate=safe_to_mutate,
        recommended_next_action=recommended_next_action,
        decision_reasons=decision_reasons,
    )
    return result
