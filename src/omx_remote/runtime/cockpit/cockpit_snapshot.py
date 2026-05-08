from __future__ import annotations

import asyncio
from pathlib import Path

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
    CockpitLaneName,
    CockpitLaneSnapshot,
    CockpitLaneState,
    CockpitSnapshot,
    CockpitSnapshotRequest,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes, RuntimeStatus
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalTrackingState,
)
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification
from omx_remote.shared.utils.json_file_store import json_file_stores


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

    runtime_status: RuntimeStatus = await runtime_status_task
    active_runtime_modes: ActiveRuntimeModes = await active_modes_task
    goal_mirror_state: CodexGoalMirrorState | None = _read_optional_goal_mirror_state(
        request.repo_root
    )
    ultrawork_state_classification, ultrawork_warnings = _read_ultrawork_state(
        Path(request.repo_root)
    )
    result: CockpitSnapshot = build_cockpit_snapshot(
        repo_root=request.repo_root,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
        goal_mirror_state=goal_mirror_state,
        ultrawork_state_classification=ultrawork_state_classification,
        ultrawork_warnings=tuple(ultrawork_warnings),
        team_names=request.team_names,
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
    )
    safe_to_mutate: bool = _derive_safe_to_mutate(
        contradictions=contradictions,
        runtime_status=runtime_status,
        active_runtime_modes=active_runtime_modes,
    )
    recommended_next_action: str = _derive_recommended_next_action(
        contradictions=contradictions,
        active_runtime_modes=active_runtime_modes,
        goal_mirror_state=goal_mirror_state,
    )
    result: CockpitSnapshot = CockpitSnapshot(
        repo_root=repo_root,
        runtime_summary=runtime_status.summary,
        active_runtime_modes=active_runtime_modes.active_modes,
        contradictions=contradictions,
        lanes=lanes,
        safe_to_mutate=safe_to_mutate,
        recommended_next_action=recommended_next_action,
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
) -> tuple[CockpitLaneSnapshot, ...]:
    """Build snapshots for the six public operating lanes.

    Args:
        repo_root [str]: Workspace root being summarized.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.
        ultrawork_state_classification [UltraworkStateClassification]: Ultrawork state classification.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork status warnings.
        team_names [tuple[str, ...]]: Explicit Team names included in this cockpit read.

    Returns:
        tuple[CockpitLaneSnapshot, ...]: Ordered lane snapshots.
    """
    lanes: tuple[CockpitLaneSnapshot, ...] = (
        _build_goal_only_lane(repo_root, goal_mirror_state),
        _build_goal_ralph_lane(repo_root, goal_mirror_state),
        _build_goal_ralph_teams_lane(repo_root, goal_mirror_state),
        _build_ultrawork_lane(ultrawork_state_classification, ultrawork_warnings),
        _build_hypergoal_lane(),
        _build_ralph_team_lane(team_names),
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


def _build_ralph_team_lane(team_names: tuple[str, ...]) -> CockpitLaneSnapshot:
    """Build the Ralph -> Team lane summary.

    Args:
        team_names [tuple[str, ...]]: Explicit Team names included in this cockpit read.

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

    team_names_text: str = ", ".join(team_names)
    lane = CockpitLaneSnapshot(
        name=CockpitLaneName.RALPH_TEAM,
        state=CockpitLaneState.UNKNOWN,
        summary=f"Explicit Team names were provided for future inspection: {team_names_text}.",
        recommended_next_action="inspect_team_status",
    )
    return lane


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


def _derive_safe_to_mutate(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
) -> bool:
    """Derive whether cockpit observations are safe for mutation.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.

    Returns:
        bool: ``True`` only when no active runtime or contradictions are visible.
    """
    has_active_runtime: bool = bool(active_runtime_modes.active_modes) or runtime_status.has_active_modes is True
    safe_to_mutate: bool = not contradictions and not has_active_runtime
    return safe_to_mutate


def _derive_recommended_next_action(
    contradictions: tuple[CockpitContradiction, ...],
    active_runtime_modes: ActiveRuntimeModes,
    goal_mirror_state: CodexGoalMirrorState | None,
) -> str:
    """Derive one top-level next action from cockpit observations.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.

    Returns:
        str: Top-level recommended next action marker.
    """
    if contradictions:
        contradiction_action: str = "inspect_runtime_contradiction"
        return contradiction_action
    if active_runtime_modes.active_modes:
        observe_action: str = "observe_active_runtime"
        return observe_action
    if goal_mirror_state and goal_mirror_state.handoff_state == CodexGoalHandoffState.AWAITING_RALPH:
        prepare_action: str = "prepare_ralph"
        return prepare_action

    default_action: str = "observe"
    return default_action
