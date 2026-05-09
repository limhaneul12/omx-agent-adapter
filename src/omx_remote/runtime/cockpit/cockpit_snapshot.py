from __future__ import annotations

import asyncio
from pathlib import Path

from omx_remote.runtime.cockpit.linked_team_discovery import (
    LinkedTeamDiscoveryResult,
    discover_linked_team_names,
    merge_explicit_and_discovered_team_names,
)
from omx_remote.runtime.goal.codex_goal_runtime import CodexGoalMirrorStateStore
from omx_remote.runtime.status.active_runtime_modes import read_active_runtime_modes
from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.runtime.ultrawork.ultrawork_control import (
    UltraworkStateClassifier,
    get_ultrawork_state_root,
    list_ultrawork_state_paths,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitContradiction,
    CockpitDecisionReason,
    CockpitLaneName,
    CockpitLaneSnapshot,
    CockpitLaneState,
    CockpitSnapshot,
    CockpitSnapshotRequest,
    CockpitStatusSourceObservation,
    CockpitStatusSourceState,
    CockpitTeamObservation,
    CockpitTeamWorkerObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes, RuntimeStatus
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
    TeamApiReadWorkerStatusRequest,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiListTasksSnapshot,
    TeamApiReadEventsSnapshot,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.schemas.teamwork.status_schemas import (
    TeamStatusRequest,
    TeamStatusSnapshot,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalTrackingState,
)
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification
from omx_remote.shared.utils.json_file_store import json_file_stores
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
    read_team_api_read_worker_status,
)
from omx_remote.teamwork.team_snapshot import read_team_status

_ACTIVE_TEAM_STATUSES: tuple[str, ...] = ("active",)


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

    runtime_status: RuntimeStatus = await runtime_status_task
    active_runtime_modes: ActiveRuntimeModes = await active_modes_task
    team_observations: tuple[CockpitTeamObservation, ...] = await team_observations_task
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
        warnings=warnings,
    )
    return result


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
    result: CockpitSnapshot = CockpitSnapshot(
        repo_root=repo_root,
        runtime_summary=runtime_status.summary,
        active_runtime_modes=active_runtime_modes.active_modes,
        discovered_teams=discovered_team_names,
        status_sources=status_sources,
        contradictions=contradictions,
        lanes=lanes,
        warnings=warnings,
        safe_to_mutate=safe_to_mutate,
        recommended_next_action=recommended_next_action,
        decision_reasons=decision_reasons,
    )
    return result


def _read_optional_goal_mirror_state(repo_root: str) -> CodexGoalMirrorState | None:
    """Read Goal mirror state when present, otherwise return absent state.

    Args:
        repo_root [str]: Workspace root whose Goal mirror should be read.

    Returns:
        CodexGoalMirrorState | None: Refreshed Goal mirror state or ``None`` when missing/invalid.
    """
    store = CodexGoalMirrorStateStore(repo_root)
    try:
        goal_mirror_state: CodexGoalMirrorState = store.read_status()
    except ValueError:
        missing_goal_mirror_state: CodexGoalMirrorState | None = None
        return missing_goal_mirror_state

    return goal_mirror_state


def _build_status_sources(
    goal_mirror_state: CodexGoalMirrorState | None,
    team_discovery: LinkedTeamDiscoveryResult,
    selected_team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    ultrawork_warnings: tuple[str, ...],
) -> tuple[CockpitStatusSourceObservation, ...]:
    """Build read-only source observations for the all-status cockpit.

    Args:
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror evidence.
        team_discovery [LinkedTeamDiscoveryResult]: Team-name discovery evidence.
        selected_team_names [tuple[str, ...]]: Team names selected for evidence reads.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime modes snapshot.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork source warnings.

    Returns:
        tuple[CockpitStatusSourceObservation, ...]: Stable source status observations.
    """
    first_team_discovery_source: str | None = None
    if team_discovery.inspected_sources:
        first_team_discovery_source = team_discovery.inspected_sources[0]

    goal_status: CockpitStatusSourceState = CockpitStatusSourceState.MISSING
    goal_detail = "No adapter-owned Goal mirror state was found."
    goal_evidence_path: str | None = None
    if goal_mirror_state is not None:
        goal_status = CockpitStatusSourceState.OBSERVED
        goal_detail = f"Goal mirror state for {goal_mirror_state.goal_id} was read."
        goal_evidence_path = f"{goal_mirror_state.working_directory}/.agent-remote/state/codex-goal.json"
    elif team_discovery.goal_mirror_failure is not None:
        goal_status = CockpitStatusSourceState.FAILED
        goal_detail = team_discovery.goal_mirror_failure
        goal_evidence_path = first_team_discovery_source

    team_discovery_status: CockpitStatusSourceState = CockpitStatusSourceState.MISSING
    team_discovery_detail = "No exact linked Team names were discovered."
    if team_discovery.discovered_team_names:
        team_discovery_status = CockpitStatusSourceState.OBSERVED
        discovered_text: str = ", ".join(team_discovery.discovered_team_names)
        team_discovery_detail = f"Discovered linked Team names: {discovered_text}."
    elif team_discovery.warnings:
        team_discovery_status = CockpitStatusSourceState.FAILED
        team_discovery_detail = "Team discovery inspected persisted state with warnings."

    team_selection_status: CockpitStatusSourceState = CockpitStatusSourceState.MISSING
    team_selection_detail = "No explicit or discovered Team names were selected."
    if selected_team_names:
        team_selection_status = CockpitStatusSourceState.OBSERVED
        selected_text: str = ", ".join(selected_team_names)
        team_selection_detail = f"Selected Team names for evidence reads: {selected_text}."

    runtime_status_source_state: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    if _runtime_status_has_uncertain_activity(runtime_status):
        runtime_status_source_state = CockpitStatusSourceState.UNKNOWN

    active_modes_detail = "No active runtime modes were reported."
    if active_runtime_modes.active_modes:
        active_modes_text: str = ", ".join(active_runtime_modes.active_modes)
        active_modes_detail = f"Active runtime modes were reported: {active_modes_text}."

    ultrawork_status: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    ultrawork_detail = "Ultrawork state was classified."
    if ultrawork_warnings:
        ultrawork_status = CockpitStatusSourceState.FAILED
        ultrawork_detail = "Ultrawork state was classified with warnings."

    sources: tuple[CockpitStatusSourceObservation, ...] = (
        CockpitStatusSourceObservation(
            name="runtime_status",
            status=runtime_status_source_state,
            detail=runtime_status.summary or "Runtime status was read.",
        ),
        CockpitStatusSourceObservation(
            name="active_runtime_modes",
            status=CockpitStatusSourceState.OBSERVED,
            detail=active_modes_detail,
        ),
        CockpitStatusSourceObservation(
            name="goal_mirror_state",
            status=goal_status,
            detail=goal_detail,
            evidence_path=goal_evidence_path,
        ),
        CockpitStatusSourceObservation(
            name="team_discovery",
            status=team_discovery_status,
            detail=team_discovery_detail,
            evidence_path=first_team_discovery_source,
        ),
        CockpitStatusSourceObservation(
            name="team_selection",
            status=team_selection_status,
            detail=team_selection_detail,
        ),
        _build_team_evidence_source(
            selected_team_names=selected_team_names,
            team_observations=team_observations,
        ),
        CockpitStatusSourceObservation(
            name="ultrawork_state",
            status=ultrawork_status,
            detail=ultrawork_detail,
        ),
    )
    return sources


def _build_team_evidence_source(
    selected_team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
) -> CockpitStatusSourceObservation:
    """Build the Team evidence source observation.

    Args:
        selected_team_names [tuple[str, ...]]: Team names selected for evidence reads.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        CockpitStatusSourceObservation: Source status for Team evidence reads.
    """
    if not selected_team_names:
        skipped_source = CockpitStatusSourceObservation(
            name="team_evidence",
            status=CockpitStatusSourceState.SKIPPED,
            detail="No Team names were selected for evidence reads.",
        )
        return skipped_source

    selected_team_text: str = ", ".join(selected_team_names)
    if not team_observations:
        failed_source = CockpitStatusSourceObservation(
            name="team_evidence",
            status=CockpitStatusSourceState.FAILED,
            detail=f"Team names were selected but no Team evidence was read: {selected_team_text}.",
        )
        return failed_source

    warnings: tuple[str, ...] = _collect_team_observation_warnings(team_observations)
    if warnings:
        warning_source = CockpitStatusSourceObservation(
            name="team_evidence",
            status=CockpitStatusSourceState.FAILED,
            detail=f"Team evidence was read with warnings for: {selected_team_text}.",
        )
        return warning_source

    observed_team_text: str = ", ".join(
        observation.team_name for observation in team_observations
    )
    observed_source = CockpitStatusSourceObservation(
        name="team_evidence",
        status=CockpitStatusSourceState.OBSERVED,
        detail=f"Team evidence was read for: {observed_team_text}.",
    )
    return observed_source


def _build_top_level_warnings(
    warnings: tuple[str, ...],
    ultrawork_warnings: tuple[str, ...],
    team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Build top-level warning labels from cockpit degradation evidence.

    Args:
        warnings [tuple[str, ...]]: Discovery or source warnings.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork read warnings.
        team_names [tuple[str, ...]]: Team names selected for Team evidence reads.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Stable ordered top-level warnings.
    """
    top_level_warnings: list[str] = [
        *warnings,
        *ultrawork_warnings,
        *_collect_team_observation_warnings(team_observations),
    ]
    if team_names and not team_observations:
        top_level_warnings.append(
            "Team names were selected but no Team evidence observations were produced."
        )

    result: tuple[str, ...] = tuple(top_level_warnings)
    return result


async def _read_team_observations(
    team_names: tuple[str, ...],
) -> tuple[CockpitTeamObservation, ...]:
    """Read explicit Team evidence for the cockpit.

    Args:
        team_names [tuple[str, ...]]: Team names requested by the caller.

    Returns:
        tuple[CockpitTeamObservation, ...]: Team evidence snapshots in caller order.
    """
    if not team_names:
        empty_observations: tuple[CockpitTeamObservation, ...] = ()
        return empty_observations

    observation_tasks = [
        asyncio.create_task(_read_team_observation(team_name)) for team_name in team_names
    ]
    observations_list: list[CockpitTeamObservation] = list(await asyncio.gather(*observation_tasks))
    observations: tuple[CockpitTeamObservation, ...] = tuple(observations_list)
    return observations


async def _read_team_observation(team_name: str) -> CockpitTeamObservation:
    """Read one Team's status, tasks, events, and worker statuses.

    Args:
        team_name [str]: Team name to inspect through read-only Team surfaces.

    Returns:
        CockpitTeamObservation: Aggregated Team evidence for the cockpit.
    """
    warnings: list[str] = []
    status_snapshot: TeamStatusSnapshot | None = None
    tasks_snapshot: TeamApiListTasksSnapshot | None = None
    events_snapshot: TeamApiReadEventsSnapshot | None = None

    try:
        status_snapshot = await read_team_status(TeamStatusRequest(team_name=team_name))
    except TeamworkSurfaceError as error:
        warnings.append(f"team status read failed for {team_name}: {error}")

    try:
        tasks_snapshot = await read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name=team_name)
        )
    except TeamworkSurfaceError as error:
        warnings.append(f"team task read failed for {team_name}: {error}")

    try:
        events_snapshot = await read_team_api_read_events(
            TeamApiReadEventsRequest(team_name=team_name)
        )
    except TeamworkSurfaceError as error:
        warnings.append(f"team event read failed for {team_name}: {error}")

    worker_names: tuple[str, ...] = _derive_observed_worker_names(
        status_snapshot=status_snapshot,
        tasks_snapshot=tasks_snapshot,
        events_snapshot=events_snapshot,
    )
    worker_statuses: tuple[CockpitTeamWorkerObservation, ...] = await _read_team_worker_observations(
        team_name=team_name,
        worker_names=worker_names,
        warnings=warnings,
    )

    status_value: str = "unknown"
    phase_value: str | None = None
    if status_snapshot is not None:
        status_value = status_snapshot.status
        phase_value = status_snapshot.phase

    task_count: int = 0
    if tasks_snapshot is not None:
        task_count = tasks_snapshot.count

    event_count: int = 0
    if events_snapshot is not None:
        event_count = events_snapshot.count

    observation = CockpitTeamObservation(
        team_name=team_name,
        status=status_value,
        phase=phase_value,
        task_count=task_count,
        event_count=event_count,
        worker_statuses=worker_statuses,
        warnings=tuple(warnings),
    )
    return observation


def _derive_observed_worker_names(
    status_snapshot: TeamStatusSnapshot | None,
    tasks_snapshot: TeamApiListTasksSnapshot | None,
    events_snapshot: TeamApiReadEventsSnapshot | None,
) -> tuple[str, ...]:
    """Derive worker names worth probing from Team status/task/event evidence.

    Args:
        status_snapshot [TeamStatusSnapshot | None]: Optional Team status evidence.
        tasks_snapshot [TeamApiListTasksSnapshot | None]: Optional Team task evidence.
        events_snapshot [TeamApiReadEventsSnapshot | None]: Optional Team event evidence.

    Returns:
        tuple[str, ...]: Stable ordered unique worker names.
    """
    worker_names: list[str] = []
    seen_worker_names: set[str] = set()

    if status_snapshot is not None:
        for worker_name in (*status_snapshot.dead_workers, *status_snapshot.non_reporting_workers):
            if worker_name not in seen_worker_names:
                seen_worker_names.add(worker_name)
                worker_names.append(worker_name)

    if tasks_snapshot is not None:
        for task_snapshot in tasks_snapshot.tasks:
            if task_snapshot.owner is not None and task_snapshot.owner not in seen_worker_names:
                seen_worker_names.add(task_snapshot.owner)
                worker_names.append(task_snapshot.owner)

    if events_snapshot is not None:
        for event_snapshot in events_snapshot.events:
            if event_snapshot.worker is not None and event_snapshot.worker not in seen_worker_names:
                seen_worker_names.add(event_snapshot.worker)
                worker_names.append(event_snapshot.worker)

    result: tuple[str, ...] = tuple(worker_names)
    return result


async def _read_team_worker_observations(
    team_name: str,
    worker_names: tuple[str, ...],
    warnings: list[str],
) -> tuple[CockpitTeamWorkerObservation, ...]:
    """Read worker-status snapshots for observed Team workers.

    Args:
        team_name [str]: Team name owning the workers.
        worker_names [tuple[str, ...]]: Worker names to inspect.
        warnings [list[str]]: Mutable warning collection for read failures.

    Returns:
        tuple[CockpitTeamWorkerObservation, ...]: Worker status observations.
    """
    worker_observations: list[CockpitTeamWorkerObservation] = []
    for worker_name in worker_names:
        try:
            worker_status: TeamApiWorkerStatusSnapshot = await read_team_api_read_worker_status(
                TeamApiReadWorkerStatusRequest(team_name=team_name, worker=worker_name)
            )
        except TeamworkSurfaceError as error:
            warnings.append(
                f"team worker-status read failed for {team_name}/{worker_name}: {error}"
            )
            continue

        worker_observation = CockpitTeamWorkerObservation(
            worker=worker_status.worker,
            state=worker_status.state,
            updated_at=worker_status.updated_at,
        )
        worker_observations.append(worker_observation)

    result: tuple[CockpitTeamWorkerObservation, ...] = tuple(worker_observations)
    return result


def _read_ultrawork_state(
    repo_root: Path,
) -> tuple[UltraworkStateClassification, tuple[str, ...]]:
    """Read current Ultrawork state classification from workspace artifacts.

    Args:
        repo_root [Path]: Workspace root whose `.omx/state` directory should be inspected.

    Returns:
        tuple[UltraworkStateClassification, tuple[str, ...]]: State classification and warnings.
    """
    existing_state_paths: list[Path] = list_ultrawork_state_paths(repo_root)
    if not existing_state_paths:
        clean_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
            UltraworkStateClassification.CLEAN,
            (),
        )
        return clean_state

    state_root: Path = get_ultrawork_state_root(repo_root)
    ultrawork_state_path: Path = state_root / "ultrawork-state.json"
    if not ultrawork_state_path.exists():
        joined_paths: str = ", ".join(str(path) for path in existing_state_paths)
        stale_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
            UltraworkStateClassification.STALE,
            (f"Known Ultrawork state files without canonical state: {joined_paths}",),
        )
        return stale_state

    state_store = json_file_stores.for_path(ultrawork_state_path)
    state_payload: dict[str, object] | None = state_store.read_object()
    if state_payload is None:
        invalid_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
            UltraworkStateClassification.INVALID,
            (f"Ultrawork state file is present but unreadable: {ultrawork_state_path}",),
        )
        return invalid_state

    classification: UltraworkStateClassification = UltraworkStateClassifier.classify_state_snapshot(
        state_payload
    )
    classified_state: tuple[UltraworkStateClassification, tuple[str, ...]] = (
        classification,
        (f"Ultrawork state path: {ultrawork_state_path}",),
    )
    return classified_state


def _build_runtime_contradictions(
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
) -> tuple[CockpitContradiction, ...]:
    """Build contradictions between runtime status and active-mode surfaces.

    Args:
        runtime_status [RuntimeStatus]: Normalized `omx status` snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Normalized active mode list.

    Returns:
        tuple[CockpitContradiction, ...]: Detected runtime contradictions.
    """
    contradictions: list[CockpitContradiction] = []
    status_active_modes: set[str] = set(runtime_status.active_mode_names)
    listed_active_modes: set[str] = set(active_runtime_modes.active_modes)
    if listed_active_modes and (
        runtime_status.has_active_modes is False or not status_active_modes
    ):
        active_modes_text: str = ", ".join(active_runtime_modes.active_modes)
        contradictions.append(
            CockpitContradiction(
                category="runtime_activity_conflict",
                message=(
                    "omx status reports no parseable active modes, but omx state list-active "
                    f"reports active modes: {active_modes_text}"
                ),
            )
        )

    result: tuple[CockpitContradiction, ...] = tuple(contradictions)
    return result


def _build_lane_snapshots(
    repo_root: str,
    goal_mirror_state: CodexGoalMirrorState | None,
    ultrawork_state_classification: UltraworkStateClassification,
    ultrawork_warnings: tuple[str, ...],
    team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[CockpitLaneSnapshot, ...]:
    """Build snapshots for the six public operating lanes.

    Args:
        repo_root [str]: Workspace root being summarized.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.
        ultrawork_state_classification [UltraworkStateClassification]: Ultrawork state classification.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork status warnings.
        team_names [tuple[str, ...]]: Explicit Team names included in this cockpit read.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[CockpitLaneSnapshot, ...]: Ordered lane snapshots.
    """
    lanes: tuple[CockpitLaneSnapshot, ...] = (
        _build_goal_only_lane(repo_root, goal_mirror_state),
        _build_goal_ralph_lane(repo_root, goal_mirror_state),
        _build_goal_ralph_teams_lane(repo_root, goal_mirror_state),
        _build_ultrawork_lane(ultrawork_state_classification, ultrawork_warnings),
        _build_hypergoal_lane(),
        _build_ralph_team_lane(team_names, team_observations),
    )
    return lanes


def _build_goal_only_lane(
    repo_root: str,
    goal_mirror_state: CodexGoalMirrorState | None,
) -> CockpitLaneSnapshot:
    """Build the Goal-only lane summary.

    Args:
        repo_root [str]: Workspace root being summarized.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.

    Returns:
        CockpitLaneSnapshot: Goal-only lane summary.
    """
    evidence_path: str = f"{repo_root}/.agent-remote/state/codex-goal.json"
    if goal_mirror_state is None:
        lane = CockpitLaneSnapshot(
            name=CockpitLaneName.GOAL_ONLY,
            state=CockpitLaneState.MISSING,
            summary="No adapter-owned Codex Goal mirror state was found.",
            evidence_paths=(),
            recommended_next_action="goal_start_or_observe",
        )
        return lane

    state: CockpitLaneState = _map_goal_tracking_state(goal_mirror_state.tracking_state)
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.GOAL_ONLY,
        state=state,
        summary=(
            f"Goal {goal_mirror_state.goal_id} is {goal_mirror_state.tracking_state} "
            f"with handoff state {goal_mirror_state.handoff_state}."
        ),
        evidence_paths=(evidence_path,),
        recommended_next_action="inspect_goal_handoff",
    )
    return lane


def _build_goal_ralph_lane(
    repo_root: str,
    goal_mirror_state: CodexGoalMirrorState | None,
) -> CockpitLaneSnapshot:
    """Build the Goal -> Ralph lane summary.

    Args:
        repo_root [str]: Workspace root being summarized.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.

    Returns:
        CockpitLaneSnapshot: Goal -> Ralph lane summary.
    """
    evidence_path: str = f"{repo_root}/.agent-remote/state/codex-goal.json"
    if goal_mirror_state is None or goal_mirror_state.execution_shape == CodexGoalExecutionShape.GOAL_ONLY:
        lane = CockpitLaneSnapshot(
            name=CockpitLaneName.GOAL_RALPH,
            state=CockpitLaneState.MISSING,
            summary="No Ralph-pipeline Goal mirror state is present.",
            evidence_paths=(),
            recommended_next_action="goal_start_with_ralph_pipeline",
        )
        return lane

    state: CockpitLaneState = _map_goal_handoff_state(goal_mirror_state.handoff_state)
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.GOAL_RALPH,
        state=state,
        summary=f"Goal handoff state is {goal_mirror_state.handoff_state}.",
        evidence_paths=(evidence_path,),
        recommended_next_action="prepare_ralph" if state == CockpitLaneState.AWAITING_RALPH else "observe_ralph",
    )
    return lane


def _build_goal_ralph_teams_lane(
    repo_root: str,
    goal_mirror_state: CodexGoalMirrorState | None,
) -> CockpitLaneSnapshot:
    """Build the Goal -> Ralph -> Team(s) lane summary.

    Args:
        repo_root [str]: Workspace root being summarized.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.

    Returns:
        CockpitLaneSnapshot: Goal -> Ralph -> Team(s) lane summary.
    """
    evidence_path: str = f"{repo_root}/.agent-remote/state/codex-goal.json"
    if goal_mirror_state is None or goal_mirror_state.team_worker_count is None:
        lane = CockpitLaneSnapshot(
            name=CockpitLaneName.GOAL_RALPH_TEAMS,
            state=CockpitLaneState.MISSING,
            summary="No Team-fanout Goal mirror state is present.",
            evidence_paths=(),
            recommended_next_action="goal_start_with_team_worker_count",
        )
        return lane

    state: CockpitLaneState = _map_goal_handoff_state(goal_mirror_state.handoff_state)
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.GOAL_RALPH_TEAMS,
        state=state,
        summary=(
            "Goal requests Ralph pipeline Team fanout with "
            f"{goal_mirror_state.team_worker_count} workers."
        ),
        evidence_paths=(evidence_path,),
        recommended_next_action="prepare_ralph" if state == CockpitLaneState.AWAITING_RALPH else "inspect_team_evidence",
    )
    return lane


def _build_ultrawork_lane(
    ultrawork_state_classification: UltraworkStateClassification,
    ultrawork_warnings: tuple[str, ...],
) -> CockpitLaneSnapshot:
    """Build the Ultrawork lane summary.

    Args:
        ultrawork_state_classification [UltraworkStateClassification]: Ultrawork state classification.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork status warnings.

    Returns:
        CockpitLaneSnapshot: Ultrawork lane summary.
    """
    state: CockpitLaneState = _map_ultrawork_state(ultrawork_state_classification)
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.ULTRAWORK_ONLY,
        state=state,
        summary=f"Ultrawork state is {ultrawork_state_classification}.",
        warnings=ultrawork_warnings,
        recommended_next_action="launch_ultrawork" if state == CockpitLaneState.CLEAN else "inspect_ultrawork_state",
    )
    return lane


def _build_hypergoal_lane() -> CockpitLaneSnapshot:
    """Build the Hypergoal planned-only lane summary.

    Returns:
        CockpitLaneSnapshot: Hypergoal lane summary.
    """
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.HYPERGOAL,
        state=CockpitLaneState.PLANNED_ONLY,
        summary="Hypergoal is currently template/planned-only; no runtime state exists.",
        recommended_next_action="use_hypergoal_template_only",
    )
    return lane


def _build_ralph_team_lane(
    team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
) -> CockpitLaneSnapshot:
    """Build the Ralph -> Team lane summary.

    Args:
        team_names [tuple[str, ...]]: Explicit Team names included in this cockpit read.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        CockpitLaneSnapshot: Ralph -> Team lane summary.
    """
    if not team_names:
        lane = CockpitLaneSnapshot(
            name=CockpitLaneName.RALPH_TEAM,
            state=CockpitLaneState.NEEDS_TEAM_NAME,
            summary="No explicit Team names were provided for Ralph-owned Team inspection.",
            recommended_next_action="rerun_with_team_name",
        )
        return lane

    if not team_observations:
        team_names_text: str = ", ".join(team_names)
        missing_observation_lane = CockpitLaneSnapshot(
            name=CockpitLaneName.RALPH_TEAM,
            state=CockpitLaneState.UNKNOWN,
            summary=f"Explicit Team names were provided but no Team evidence was read: {team_names_text}.",
            recommended_next_action="inspect_team_status",
        )
        return missing_observation_lane

    state: CockpitLaneState = _derive_ralph_team_lane_state(team_observations)
    summary: str = _summarize_team_observations(team_observations)
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.RALPH_TEAM,
        state=state,
        summary=summary,
        team_observations=team_observations,
        warnings=_collect_team_observation_warnings(team_observations),
        recommended_next_action="inspect_team_evidence",
    )
    return lane


def _derive_ralph_team_lane_state(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> CockpitLaneState:
    """Derive the Ralph -> Team lane state from Team observations.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        CockpitLaneState: Aggregate Ralph -> Team lane state.
    """
    has_active_team: bool = _team_observations_include_active_runtime(team_observations)
    if has_active_team:
        active_state: CockpitLaneState = CockpitLaneState.ACTIVE
        return active_state

    all_missing: bool = all(observation.status == "missing" for observation in team_observations)
    if all_missing:
        missing_state: CockpitLaneState = CockpitLaneState.MISSING
        return missing_state

    unknown_state: CockpitLaneState = CockpitLaneState.UNKNOWN
    return unknown_state


def _summarize_team_observations(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> str:
    """Summarize Team observations for the Ralph -> Team cockpit lane.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        str: Compact human-readable Team evidence summary.
    """
    summary_parts: list[str] = []
    for observation in team_observations:
        phase_text: str = "no phase"
        if observation.phase is not None:
            phase_text = observation.phase
        worker_count: int = len(observation.worker_statuses)
        summary_parts.append(
            f"{observation.team_name}: {observation.status} ({phase_text}), "
            f"{observation.task_count} tasks, {observation.event_count} events, "
            f"{worker_count} worker statuses"
        )

    summary: str = "; ".join(summary_parts)
    return summary


def _collect_team_observation_warnings(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Collect warnings from Team observations.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Flattened warning texts.
    """
    warnings: list[str] = []
    for observation in team_observations:
        warnings.extend(observation.warnings)

    result: tuple[str, ...] = tuple(warnings)
    return result


def _map_goal_tracking_state(tracking_state: CodexGoalTrackingState) -> CockpitLaneState:
    """Map native Goal tracking state into cockpit lane state.

    Args:
        tracking_state [CodexGoalTrackingState]: Goal tracking state.

    Returns:
        CockpitLaneState: Cockpit state marker.
    """
    if tracking_state in (CodexGoalTrackingState.ACTIVE, CodexGoalTrackingState.STARTING):
        active_state: CockpitLaneState = CockpitLaneState.ACTIVE
        return active_state
    if tracking_state == CodexGoalTrackingState.ENDED:
        ended_state: CockpitLaneState = CockpitLaneState.ENDED
        return ended_state

    unknown_state: CockpitLaneState = CockpitLaneState.UNKNOWN
    return unknown_state


def _map_goal_handoff_state(handoff_state: CodexGoalHandoffState) -> CockpitLaneState:
    """Map Goal handoff state into cockpit lane state.

    Args:
        handoff_state [CodexGoalHandoffState]: Goal handoff state.

    Returns:
        CockpitLaneState: Cockpit state marker.
    """
    if handoff_state == CodexGoalHandoffState.AWAITING_RALPH:
        awaiting_state: CockpitLaneState = CockpitLaneState.AWAITING_RALPH
        return awaiting_state
    if handoff_state == CodexGoalHandoffState.RALPH_STARTED:
        ralph_started_state: CockpitLaneState = CockpitLaneState.RALPH_STARTED
        return ralph_started_state
    if handoff_state == CodexGoalHandoffState.GOAL_ONLY:
        missing_state: CockpitLaneState = CockpitLaneState.MISSING
        return missing_state

    unknown_state: CockpitLaneState = CockpitLaneState.UNKNOWN
    return unknown_state


def _map_ultrawork_state(
    ultrawork_state_classification: UltraworkStateClassification,
) -> CockpitLaneState:
    """Map Ultrawork classification into cockpit lane state.

    Args:
        ultrawork_state_classification [UltraworkStateClassification]: Ultrawork state classification.

    Returns:
        CockpitLaneState: Cockpit state marker.
    """
    mapping: dict[UltraworkStateClassification, CockpitLaneState] = {
        UltraworkStateClassification.CLEAN: CockpitLaneState.CLEAN,
        UltraworkStateClassification.RESUMABLE: CockpitLaneState.RESUMABLE,
        UltraworkStateClassification.STALE: CockpitLaneState.STALE,
        UltraworkStateClassification.TERMINAL: CockpitLaneState.TERMINAL,
        UltraworkStateClassification.MISSING: CockpitLaneState.MISSING,
        UltraworkStateClassification.INVALID: CockpitLaneState.INVALID,
    }
    state: CockpitLaneState = mapping[ultrawork_state_classification]
    return state


def _runtime_status_has_uncertain_activity(runtime_status: RuntimeStatus) -> bool:
    """Return whether runtime activity is unknown enough to require inspection.

    Args:
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.

    Returns:
        bool: ``True`` when `omx status` did not produce a definitive activity signal.
    """
    has_uncertain_activity: bool = runtime_status.has_active_modes is None
    return has_uncertain_activity


def _derive_safe_to_mutate(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    team_observations: tuple[CockpitTeamObservation, ...],
) -> bool:
    """Derive whether cockpit observations are safe for mutation.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        bool: ``True`` only when no active runtime, active Team, or contradictions are visible.
    """
    has_active_runtime: bool = bool(active_runtime_modes.active_modes) or runtime_status.has_active_modes is True
    has_uncertain_runtime: bool = _runtime_status_has_uncertain_activity(runtime_status)
    has_active_team: bool = _team_observations_include_active_runtime(team_observations)
    safe_to_mutate: bool = (
        not contradictions
        and not has_active_runtime
        and not has_uncertain_runtime
        and not has_active_team
    )
    return safe_to_mutate


def _derive_recommended_next_action(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    goal_mirror_state: CodexGoalMirrorState | None,
    team_observations: tuple[CockpitTeamObservation, ...],
) -> str:
    """Derive one top-level next action from cockpit observations.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        str: Top-level recommended next action marker.
    """
    if contradictions:
        contradiction_action: str = "inspect_runtime_contradiction"
        return contradiction_action
    if active_runtime_modes.active_modes or runtime_status.has_active_modes is True:
        observe_action: str = "observe_active_runtime"
        return observe_action
    if _runtime_status_has_uncertain_activity(runtime_status):
        inspect_runtime_action: str = "inspect_runtime_status"
        return inspect_runtime_action
    if _team_observations_include_active_runtime(team_observations):
        inspect_team_action: str = "inspect_team_evidence"
        return inspect_team_action
    if goal_mirror_state and goal_mirror_state.handoff_state == CodexGoalHandoffState.AWAITING_RALPH:
        prepare_action: str = "prepare_ralph"
        return prepare_action

    default_action: str = "observe"
    return default_action


def _build_decision_reasons(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    goal_mirror_state: CodexGoalMirrorState | None,
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[CockpitDecisionReason, ...]:
    """Build evidence-backed explanations for top-level cockpit guidance.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[CockpitDecisionReason, ...]: Ordered reasons matching top-level cockpit guidance.
    """
    reasons: list[CockpitDecisionReason] = [
        CockpitDecisionReason(
            category="runtime_contradiction",
            detail=contradiction.message,
            source_names=("runtime_status", "active_runtime_modes"),
        )
        for contradiction in contradictions
    ]

    if active_runtime_modes.active_modes:
        active_modes_text: str = ", ".join(active_runtime_modes.active_modes)
        reasons.append(
            CockpitDecisionReason(
                category="active_runtime_evidence",
                detail=f"Active runtime modes are present: {active_modes_text}.",
                source_names=("active_runtime_modes",),
            )
        )
    elif runtime_status.has_active_modes is True:
        reasons.append(
            CockpitDecisionReason(
                category="active_runtime_evidence",
                detail="Runtime status reports active modes without a parsed active-mode list.",
                source_names=("runtime_status",),
            )
        )
    elif _runtime_status_has_uncertain_activity(runtime_status):
        reasons.append(
            CockpitDecisionReason(
                category="runtime_status_uncertain",
                detail="Runtime status could not determine whether modes are active.",
                source_names=("runtime_status",),
            )
        )

    active_team_names: tuple[str, ...] = _collect_active_team_names(team_observations)
    if active_team_names:
        active_team_text: str = ", ".join(active_team_names)
        reasons.append(
            CockpitDecisionReason(
                category="active_team_evidence",
                detail=f"Active Team evidence is present for: {active_team_text}.",
                source_names=("team_evidence",),
            )
        )

    if goal_mirror_state and goal_mirror_state.handoff_state == CodexGoalHandoffState.AWAITING_RALPH:
        reasons.append(
            CockpitDecisionReason(
                category="goal_awaiting_ralph",
                detail=f"Goal {goal_mirror_state.goal_id} is awaiting Ralph handoff.",
                source_names=("goal_mirror_state",),
            )
        )

    if not reasons:
        reasons.append(
            CockpitDecisionReason(
                category="no_blocking_evidence",
                detail="No active runtime, active Team, contradiction, or pending Goal handoff evidence was found.",
                source_names=("runtime_status", "active_runtime_modes"),
            )
        )

    result: tuple[CockpitDecisionReason, ...] = tuple(reasons)
    return result


def _collect_active_team_names(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Collect Team names whose observations show explicit active evidence.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Team names with explicit active status.
    """
    active_team_names: list[str] = [
        observation.team_name
        for observation in team_observations
        if observation.status in _ACTIVE_TEAM_STATUSES
    ]
    result: tuple[str, ...] = tuple(active_team_names)
    return result


def _team_observations_include_active_runtime(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> bool:
    """Detect whether Team observations show active Team runtime evidence.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        bool: ``True`` when at least one Team observation has an explicit active status.
    """
    has_active_team: bool = any(
        observation.status in _ACTIVE_TEAM_STATUSES for observation in team_observations
    )
    return has_active_team
