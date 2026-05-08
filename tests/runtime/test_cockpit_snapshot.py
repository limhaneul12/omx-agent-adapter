import asyncio
from pathlib import Path

from omx_remote.runtime.cockpit import cockpit_snapshot
from omx_remote.runtime.cockpit.cockpit_snapshot import (
    build_cockpit_snapshot,
    read_cockpit_snapshot,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitLaneName,
    CockpitLaneState,
    CockpitSnapshotRequest,
    CockpitTeamObservation,
    CockpitTeamWorkerObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes, RuntimeStatus
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiReadWorkerStatusRequest,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiEventSnapshot,
    TeamApiListTasksSnapshot,
    TeamApiReadEventsSnapshot,
    TeamApiTaskSnapshot,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.schemas.teamwork.status_schemas import TeamStatusSnapshot
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


def test_cockpit_promotes_explicit_team_observation_into_ralph_team_lane(
    tmp_path: Path,
) -> None:
    team_observation = CockpitTeamObservation(
        team_name="alpha-team",
        status="active",
        phase="team-exec",
        task_count=2,
        event_count=3,
        worker_statuses=(
            CockpitTeamWorkerObservation(
                worker="worker-1",
                state="running",
                updated_at="2026-05-08T00:00:00.000Z",
            ),
        ),
        warnings=(),
    )

    snapshot = build_cockpit_snapshot(
        repo_root=str(tmp_path),
        runtime_status=_idle_runtime_status(),
        active_runtime_modes=ActiveRuntimeModes(active_modes=()),
        goal_mirror_state=None,
        ultrawork_state_classification=UltraworkStateClassification.CLEAN,
        ultrawork_warnings=(),
        team_names=("alpha-team",),
        team_observations=(team_observation,),
    )

    ralph_team_lane = next(
        lane for lane in snapshot.lanes if lane.name == CockpitLaneName.RALPH_TEAM
    )

    assert ralph_team_lane.state == CockpitLaneState.ACTIVE
    assert "alpha-team" in ralph_team_lane.summary
    assert "2 tasks" in ralph_team_lane.summary
    assert "3 events" in ralph_team_lane.summary
    assert ralph_team_lane.team_observations == (team_observation,)
    assert ralph_team_lane.recommended_next_action == "inspect_team_evidence"


def test_read_cockpit_snapshot_reads_team_surfaces_and_worker_statuses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    worker_status_calls: list[tuple[str, str]] = []

    async def fake_read_runtime_status() -> RuntimeStatus:
        return _idle_runtime_status()

    async def fake_read_active_runtime_modes() -> ActiveRuntimeModes:
        return ActiveRuntimeModes(active_modes=())

    async def fake_read_team_status(request) -> TeamStatusSnapshot:
        return TeamStatusSnapshot(
            team_name=request.team_name,
            status="active",
            phase="team-exec",
        )

    async def fake_read_tasks(request) -> TeamApiListTasksSnapshot:
        return TeamApiListTasksSnapshot(
            count=1,
            tasks=(
                TeamApiTaskSnapshot(
                    id="task-1",
                    subject="Implement Team cockpit evidence.",
                    status="completed",
                    owner="worker-1",
                ),
            ),
        )

    async def fake_read_events(request) -> TeamApiReadEventsSnapshot:
        return TeamApiReadEventsSnapshot(
            count=1,
            cursor="cursor-1",
            events=(
                TeamApiEventSnapshot(
                    type="task_completed",
                    worker="worker-2",
                    task_id="task-1",
                ),
            ),
        )

    async def fake_read_worker_status(
        request: TeamApiReadWorkerStatusRequest,
    ) -> TeamApiWorkerStatusSnapshot:
        worker_status_calls.append((request.team_name, request.worker))
        return TeamApiWorkerStatusSnapshot(
            worker=request.worker,
            state="running",
            updated_at="2026-05-08T00:00:00.000Z",
        )

    monkeypatch.setattr(cockpit_snapshot, "read_runtime_status", fake_read_runtime_status)
    monkeypatch.setattr(
        cockpit_snapshot,
        "read_active_runtime_modes",
        fake_read_active_runtime_modes,
    )
    monkeypatch.setattr(cockpit_snapshot, "read_team_status", fake_read_team_status)
    monkeypatch.setattr(cockpit_snapshot, "read_team_api_list_tasks", fake_read_tasks)
    monkeypatch.setattr(cockpit_snapshot, "read_team_api_read_events", fake_read_events)
    monkeypatch.setattr(
        cockpit_snapshot,
        "read_team_api_read_worker_status",
        fake_read_worker_status,
    )

    snapshot = asyncio.run(
        read_cockpit_snapshot(
            CockpitSnapshotRequest(repo_root=str(tmp_path), team_names=("alpha-team",))
        )
    )

    ralph_team_lane = next(
        lane for lane in snapshot.lanes if lane.name == CockpitLaneName.RALPH_TEAM
    )
    observation = ralph_team_lane.team_observations[0]

    assert observation.team_name == "alpha-team"
    assert observation.status == "active"
    assert observation.task_count == 1
    assert observation.event_count == 1
    assert tuple(worker.worker for worker in observation.worker_statuses) == (
        "worker-1",
        "worker-2",
    )
    assert worker_status_calls == [
        ("alpha-team", "worker-1"),
        ("alpha-team", "worker-2"),
    ]
