import asyncio
from pathlib import Path

from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.runtime.cockpit.snapshot.builder import build_cockpit_snapshot
from omx_remote.runtime.cockpit.sources.agent_config import (
    summarize_cockpit_agent_config,
)
from omx_remote.runtime.cockpit.sources.capability_snapshot import (
    read_cockpit_capabilities,
)
from omx_remote.runtime.cockpit.sources.command_recipes import (
    summarize_cockpit_command_recipes,
)
from omx_remote.runtime.cockpit.sources.github_pr_status.reader import (
    read_github_pull_request_status,
)
from omx_remote.runtime.cockpit.sources.goal_mirror import (
    _read_optional_goal_mirror_state,
)
from omx_remote.runtime.cockpit.sources.status import (
    _build_status_sources,
    _build_top_level_warnings,
)
from omx_remote.runtime.cockpit.sources.ultrawork import _read_ultrawork_state
from omx_remote.runtime.cockpit.team_evidence.discovery import (
    LinkedTeamDiscoveryResult,
    discover_linked_team_names,
    merge_explicit_and_discovered_team_names,
)
from omx_remote.runtime.cockpit.team_evidence.reader import _read_team_observations
from omx_remote.runtime.status.active_runtime_modes import read_active_runtime_modes
from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
    CockpitCapabilitiesSnapshot,
    CockpitCommandRecipeSummary,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitPullRequestObservation,
    CockpitSnapshot,
    CockpitSnapshotRequest,
    CockpitStatusSourceObservation,
    CockpitStatusSourceState,
    CockpitTeamObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes, RuntimeStatus


async def read_cockpit_snapshot(
    request: CockpitSnapshotRequest,
) -> CockpitSnapshot:
    """Read a repo-scoped cockpit snapshot from existing read-only surfaces.

    Args:
        request [CockpitSnapshotRequest]: Repo root and optional explicit Team names to inspect.

    Returns:
        CockpitSnapshot: Aggregated read-only cockpit snapshot.
    """
    runtime_status_task = asyncio.create_task(read_runtime_status())
    active_modes_task = asyncio.create_task(read_active_runtime_modes())

    goal_mirror_state: CodexGoalMirrorState | None = _read_optional_goal_mirror_state(
        request.repo_root
    )
    team_discovery: LinkedTeamDiscoveryResult = discover_linked_team_names(
        request.repo_root
    )
    selected_team_names: tuple[str, ...] = merge_explicit_and_discovered_team_names(
        explicit_team_names=request.team_names,
        discovered_team_names=team_discovery.discovered_team_names,
    )
    team_observations_task = asyncio.create_task(
        _read_team_observations(selected_team_names)
    )
    pull_request_status_task = asyncio.create_task(
        read_github_pull_request_status(request.repo_root)
    )
    capabilities_task = asyncio.create_task(run_blocking_call(read_cockpit_capabilities))
    configured_agents_task = asyncio.create_task(
        run_blocking_call(summarize_cockpit_agent_config, request.repo_root)
    )
    command_recipes_task = asyncio.create_task(
        run_blocking_call(summarize_cockpit_command_recipes, request.repo_root)
    )

    runtime_status: RuntimeStatus = await runtime_status_task
    active_runtime_modes: ActiveRuntimeModes = await active_modes_task
    team_observations: tuple[CockpitTeamObservation, ...] = await team_observations_task
    pull_request_status: CockpitPullRequestObservation = await pull_request_status_task
    capabilities: CockpitCapabilitiesSnapshot = await capabilities_task
    configured_agents: CockpitAgentConfigSummary = await configured_agents_task
    command_recipes: CockpitCommandRecipeSummary = await command_recipes_task
    ultrawork_state_classification, ultrawork_warnings = _read_ultrawork_state(
        Path(request.repo_root)
    )
    status_sources: tuple[CockpitStatusSourceObservation, ...] = _build_status_sources(
        goal_mirror_state=goal_mirror_state,
        team_discovery=team_discovery,
        selected_team_names=selected_team_names,
        team_observations=team_observations,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
        ultrawork_warnings=tuple(ultrawork_warnings),
        pull_request_status=pull_request_status,
    )
    extended_status_sources: tuple[CockpitStatusSourceObservation, ...] = (
        *status_sources,
        *_build_capability_route_status_sources(
            capabilities=capabilities,
            configured_agents=configured_agents,
            command_recipes=command_recipes,
        ),
    )
    warnings: tuple[str, ...] = _build_top_level_warnings(
        warnings=(
            *team_discovery.warnings,
            *capabilities.codex.warnings,
            *capabilities.omx.warnings,
            *configured_agents.warnings,
            *command_recipes.warnings,
        ),
        ultrawork_warnings=tuple(ultrawork_warnings),
        team_names=selected_team_names,
        team_observations=team_observations,
    )
    result: CockpitSnapshot = build_cockpit_snapshot(
        repo_root=request.repo_root,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
        goal_mirror_state=goal_mirror_state,
        ultrawork_state_classification=ultrawork_state_classification,
        ultrawork_warnings=tuple(ultrawork_warnings),
        team_names=selected_team_names,
        team_observations=team_observations,
        discovered_team_names=team_discovery.discovered_team_names,
        status_sources=extended_status_sources,
        pull_request_status=pull_request_status,
        capabilities=capabilities,
        configured_agents=configured_agents,
        command_recipes=command_recipes,
        warnings=warnings,
    )
    return result


def _build_capability_route_status_sources(
    capabilities: CockpitCapabilitiesSnapshot,
    configured_agents: CockpitAgentConfigSummary,
    command_recipes: CockpitCommandRecipeSummary,
) -> tuple[CockpitStatusSourceObservation, ...]:
    """Build cockpit source observations for capability and route evidence.

    Args:
        capabilities [CockpitCapabilitiesSnapshot]: Native capability evidence.
        configured_agents [CockpitAgentConfigSummary]: Agent config summary.
        command_recipes [CockpitCommandRecipeSummary]: Command recipe summary.

    Returns:
        tuple[CockpitStatusSourceObservation, ...]: Capability/config/recipe/route sources.
    """
    capability_status: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    if not capabilities.codex.available and not capabilities.omx.available:
        capability_status = CockpitStatusSourceState.MISSING
    elif capabilities.codex.warnings or capabilities.omx.warnings:
        capability_status = CockpitStatusSourceState.FAILED

    agent_status: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    if configured_agents.warnings:
        agent_status = CockpitStatusSourceState.FAILED

    recipe_status: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    if command_recipes.warnings:
        recipe_status = CockpitStatusSourceState.FAILED

    sources: tuple[CockpitStatusSourceObservation, ...] = (
        CockpitStatusSourceObservation(
            name="capabilities",
            status=capability_status,
            detail=(
                f"Codex available={capabilities.codex.available}; "
                f"OMX available={capabilities.omx.available}."
            ),
        ),
        CockpitStatusSourceObservation(
            name="configured_agents",
            status=agent_status,
            detail=(
                f"{configured_agents.enabled_count} enabled and "
                f"{configured_agents.disabled_count} disabled configured agents."
            ),
            evidence_path=configured_agents.config_path,
        ),
        CockpitStatusSourceObservation(
            name="command_recipes",
            status=recipe_status,
            detail=f"{command_recipes.available_count} command recipes are available.",
        ),
        CockpitStatusSourceObservation(
            name="route_policy",
            status=CockpitStatusSourceState.OBSERVED,
            detail="Route recommendations are derived from capabilities, config, recipes, and runtime safety evidence.",
        ),
    )
    return sources
