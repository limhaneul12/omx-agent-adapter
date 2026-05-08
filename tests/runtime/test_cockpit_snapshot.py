from pathlib import Path

from omx_remote.runtime.cockpit.cockpit_snapshot import build_cockpit_snapshot
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitLaneName,
    CockpitLaneState,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes, RuntimeStatus
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalMirrorSource,
    CodexGoalReviewPolicy,
    CodexGoalTrackingState,
)
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification


def _idle_runtime_status() -> RuntimeStatus:
    return RuntimeStatus(
        summary="No active modes.",
        has_active_modes=False,
        active_mode_names=(),
        mode_snapshots=(),
        anomalies=(),
    )


def _goal_mirror_state(repo_root: Path) -> CodexGoalMirrorState:
    return CodexGoalMirrorState(
        goal_id="goal-cockpit",
        objective_text="Build cockpit status.",
        source=CodexGoalMirrorSource.CODEX_GOAL,
        execution_shape=CodexGoalExecutionShape.RALPH_PIPELINE,
        review_policy=CodexGoalReviewPolicy.REVIEW_REQUIRED,
        team_worker_count=4,
        working_directory=str(repo_root),
        codex_command=("codex", "--enable", "goals"),
        session_locator="agent-remote-goal-goal-cockpit",
        process_id=1234,
        launched_at="2026-05-08T00:00:00+00:00",
        handoff_state=CodexGoalHandoffState.AWAITING_RALPH,
        tracking_state=CodexGoalTrackingState.ENDED,
    )


def test_cockpit_flags_conflicting_runtime_activity_sources(tmp_path: Path) -> None:
    snapshot = build_cockpit_snapshot(
        repo_root=str(tmp_path),
        runtime_status=_idle_runtime_status(),
        active_runtime_modes=ActiveRuntimeModes(active_modes=("run",)),
        goal_mirror_state=None,
        ultrawork_state_classification=UltraworkStateClassification.CLEAN,
        ultrawork_warnings=(),
        team_names=(),
    )

    assert snapshot.safe_to_mutate is False
    assert snapshot.recommended_next_action == "inspect_runtime_contradiction"
    assert snapshot.contradictions[0].category == "runtime_activity_conflict"
    assert "run" in snapshot.contradictions[0].message


def test_cockpit_flags_empty_parsed_runtime_with_active_state_list(tmp_path: Path) -> None:
    runtime_status = RuntimeStatus(
        summary="native-stop: inactive (phase: n/a)\nNo active modes.",
        has_active_modes=True,
        active_mode_names=(),
        mode_snapshots=(),
        anomalies=(),
    )

    snapshot = build_cockpit_snapshot(
        repo_root=str(tmp_path),
        runtime_status=runtime_status,
        active_runtime_modes=ActiveRuntimeModes(active_modes=("run",)),
        goal_mirror_state=None,
        ultrawork_state_classification=UltraworkStateClassification.CLEAN,
        ultrawork_warnings=(),
        team_names=(),
    )

    assert snapshot.safe_to_mutate is False
    assert snapshot.recommended_next_action == "inspect_runtime_contradiction"
    assert snapshot.contradictions[0].category == "runtime_activity_conflict"
    assert "run" in snapshot.contradictions[0].message


def test_cockpit_reports_all_operating_lanes_with_honest_baseline_states(tmp_path: Path) -> None:
    snapshot = build_cockpit_snapshot(
        repo_root=str(tmp_path),
        runtime_status=_idle_runtime_status(),
        active_runtime_modes=ActiveRuntimeModes(active_modes=()),
        goal_mirror_state=_goal_mirror_state(tmp_path),
        ultrawork_state_classification=UltraworkStateClassification.CLEAN,
        ultrawork_warnings=(),
        team_names=(),
    )

    lane_states = {lane.name: lane.state for lane in snapshot.lanes}

    assert tuple(lane_states) == (
        CockpitLaneName.GOAL_ONLY,
        CockpitLaneName.GOAL_RALPH,
        CockpitLaneName.GOAL_RALPH_TEAMS,
        CockpitLaneName.ULTRAWORK_ONLY,
        CockpitLaneName.HYPERGOAL,
        CockpitLaneName.RALPH_TEAM,
    )
    assert lane_states[CockpitLaneName.GOAL_ONLY] == CockpitLaneState.ENDED
    assert lane_states[CockpitLaneName.GOAL_RALPH] == CockpitLaneState.AWAITING_RALPH
    assert lane_states[CockpitLaneName.GOAL_RALPH_TEAMS] == CockpitLaneState.AWAITING_RALPH
    assert lane_states[CockpitLaneName.ULTRAWORK_ONLY] == CockpitLaneState.CLEAN
    assert lane_states[CockpitLaneName.HYPERGOAL] == CockpitLaneState.PLANNED_ONLY
    assert lane_states[CockpitLaneName.RALPH_TEAM] == CockpitLaneState.NEEDS_TEAM_NAME
