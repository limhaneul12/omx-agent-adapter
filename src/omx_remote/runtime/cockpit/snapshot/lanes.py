from omx_remote.runtime.cockpit.snapshot.decisions import (
    _team_observations_include_active_runtime,
)
from omx_remote.runtime.cockpit.team_evidence.summary import (
    _collect_team_observation_warnings,
    _summarize_team_observations,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitLaneName,
    CockpitLaneSnapshot,
    CockpitLaneState,
    CockpitTeamObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalTrackingState,
)
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification


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
