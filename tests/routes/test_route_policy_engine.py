from pathlib import Path

from omx_remote.runtime.routes.route_policy_engine import build_route_policy_result
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
    CockpitCapabilitiesSnapshot,
    CockpitCapabilityCommand,
    CockpitCommandRecipeSummary,
    CockpitRuntimeCapability,
)
from omx_remote.schemas.routes.route_policy_schemas import (
    RouteName,
    RouteRecommendationStatus,
)


def _capabilities() -> CockpitCapabilitiesSnapshot:
    return CockpitCapabilitiesSnapshot(
        codex=CockpitRuntimeCapability(
            name="codex",
            available=True,
            executable_path="/usr/bin/codex",
            version="codex 0.133.0",
            commands=(
                CockpitCapabilityCommand(
                    name="exec_json",
                    available=True,
                    detail="codex exec --json is available.",
                ),
            ),
        ),
        omx=CockpitRuntimeCapability(
            name="omx",
            available=True,
            executable_path="/usr/bin/omx",
            version="omx 0.18.0",
            commands=(
                CockpitCapabilityCommand(
                    name="ultragoal",
                    available=True,
                    detail="omx ultragoal --help succeeded.",
                ),
                CockpitCapabilityCommand(
                    name="team",
                    available=True,
                    detail="omx team --help succeeded.",
                ),
            ),
        ),
    )


def _capabilities_without_ultragoal() -> CockpitCapabilitiesSnapshot:
    return CockpitCapabilitiesSnapshot(
        codex=CockpitRuntimeCapability(
            name="codex",
            available=True,
            executable_path="/usr/bin/codex",
            version="codex 0.133.0",
            commands=(
                CockpitCapabilityCommand(
                    name="exec_json",
                    available=True,
                    detail="codex exec --json is available.",
                ),
            ),
        ),
        omx=CockpitRuntimeCapability(
            name="omx",
            available=True,
            executable_path="/usr/bin/omx",
            version="omx 0.18.0",
            commands=(
                CockpitCapabilityCommand(
                    name="team",
                    available=True,
                    detail="omx team --help succeeded.",
                ),
            ),
        ),
    )


def _agents() -> CockpitAgentConfigSummary:
    return CockpitAgentConfigSummary(
        config_path=".agent-remote.toml",
        total_count=2,
        enabled_count=1,
        disabled_count=1,
        enabled_agent_ids=("implementer",),
        warnings=(),
    )


def _recipes() -> CockpitCommandRecipeSummary:
    return CockpitCommandRecipeSummary(
        available_count=3,
        builtin_count=2,
        repo_count=1,
        qualified_ids=(
            "builtin:review-diff",
            "builtin:verify-handoff-plus",
            "repo:implement-with-review",
        ),
        warnings=(),
    )


def test_policy_prefers_ultragoal_for_durable_roadmap(tmp_path: Path) -> None:
    result = build_route_policy_result(
        task="execute this roadmap with multiple goals",
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=True,
        active_runtime_modes=(),
    )

    assert result.recommendations[0].route == RouteName.OMX_ULTRAGOAL
    assert result.recommendations[0].status == RouteRecommendationStatus.RECOMMENDED
    assert result.recommendations[0].confidence == "high"
    assert "durable" in result.recommendations[0].reason


def test_policy_explains_missing_ultragoal_capability_for_roadmap(
    tmp_path: Path,
) -> None:
    result = build_route_policy_result(
        task="execute this roadmap with multiple goals",
        cwd=tmp_path,
        capabilities=_capabilities_without_ultragoal(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=True,
        active_runtime_modes=(),
    )
    blocked_routes = {alternative.route: alternative for alternative in result.blocked_alternatives}

    assert result.recommendations[0].route == RouteName.CODEX_EXEC
    assert RouteName.OMX_ULTRAGOAL in blocked_routes
    assert blocked_routes[RouteName.OMX_ULTRAGOAL].blocked_by == (
        "omx ultragoal command is unavailable",
    )


def test_policy_does_not_prefer_ultragoal_for_small_verification(
    tmp_path: Path,
) -> None:
    result = build_route_policy_result(
        task="verify current repo state",
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=True,
        active_runtime_modes=(),
    )

    assert result.recommendations[0].route != RouteName.OMX_ULTRAGOAL
    assert result.recommendations[0].route == RouteName.PROJECT_COMMAND
    assert result.recommendations[0].command_id == "builtin:verify-handoff-plus"


def test_policy_prefers_review_diff_recipe_for_review_task(tmp_path: Path) -> None:
    result = build_route_policy_result(
        task="review current diff",
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=True,
        active_runtime_modes=(),
    )

    assert result.recommendations[0].route == RouteName.PROJECT_COMMAND
    assert result.recommendations[0].command_id == "builtin:review-diff"


def test_policy_blocks_team_route_when_runtime_is_active(tmp_path: Path) -> None:
    result = build_route_policy_result(
        task="split this refactor across workers",
        cwd=tmp_path,
        capabilities=_capabilities(),
        agent_summary=_agents(),
        recipe_summary=_recipes(),
        safe_to_mutate=False,
        active_runtime_modes=("ultragoal",),
    )

    blocked_routes = {alternative.route: alternative for alternative in result.blocked_alternatives}

    assert RouteName.OMX_TEAM in blocked_routes
    assert blocked_routes[RouteName.OMX_TEAM].status == RouteRecommendationStatus.BLOCKED
    assert blocked_routes[RouteName.OMX_TEAM].blocked_by == (
        "active runtime modes: ultragoal",
    )
