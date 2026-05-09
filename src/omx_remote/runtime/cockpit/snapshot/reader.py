import asyncio
from pathlib import Path

from omx_remote.runtime.cockpit.snapshot.builder import build_cockpit_snapshot
from omx_remote.runtime.cockpit.sources.github_pr_status import (
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
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitPullRequestObservation,
    CockpitSnapshot,
    CockpitSnapshotRequest,
    CockpitStatusSourceObservation,
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

    runtime_status: RuntimeStatus = await runtime_status_task
    active_runtime_modes: ActiveRuntimeModes = await active_modes_task
    team_observations: tuple[CockpitTeamObservation, ...] = await team_observations_task
    pull_request_status: CockpitPullRequestObservation = await pull_request_status_task
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
    warnings: tuple[str, ...] = _build_top_level_warnings(
        warnings=team_discovery.warnings,
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
        status_sources=status_sources,
        pull_request_status=pull_request_status,
        warnings=warnings,
    )
    return result
