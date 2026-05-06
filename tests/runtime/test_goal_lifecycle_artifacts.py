from pathlib import Path

import pytest

from omx_remote.runtime.goal.codex_goal_supervisor import (
    restore_goal_lifecycle_state as supervisor_restore_goal_lifecycle_state,
)
from omx_remote.runtime.goal.goal_lifecycle_artifacts import (
    CodexGoalLifecycleArtifactStore,
    get_goal_lifecycle_artifact_path,
    restore_goal_lifecycle_state,
)
from omx_remote.schemas.codex_goal.lifecycle_schemas import (
    CodexGoalLifecycleArtifactBundle,
    CodexGoalLifecycleDecisionResult,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult
from omx_remote.schemas.teamwork.admin_aggregation_schemas import TeamAdminAggregationReport


def _mirror_state(goal_id: str = "goal-restore") -> CodexGoalMirrorState:
    return CodexGoalMirrorState(
        goal_id=goal_id,
        objective_text="Restore Team Admin lifecycle artifacts.",
        source="codex_goal",
        execution_shape="ralph_pipeline",
        review_policy="continue_automatically",
        team_worker_count=2,
        working_directory="/tmp/project",
        codex_command=["codex", "--enable", "goals"],
        session_locator=f"agent-remote-goal-{goal_id}",
        process_id=1234,
        launched_at="2026-05-05T12:00:00+00:00",
        handoff_state="ralph_started",
        tracking_state="active",
    )


def _aggregation_report() -> TeamAdminAggregationReport:
    return TeamAdminAggregationReport(
        admin_id="team-admin",
        aggregation_state="ready_for_ralph_review",
        merge_ready=True,
        final_report_required=True,
        completed_workers=["worker-1", "worker-2"],
        missing_workers=[],
        blocked_workers=[],
        incomplete_workers=[],
        requires_human_review=False,
        requires_llm_review=True,
        task_count=2,
        event_count=2,
        summary="Team Admin collected all worker results.",
    )


def _ralph_review_result() -> RalphPostTeamReviewResult:
    return RalphPostTeamReviewResult(
        decision="complete",
        complete=True,
        follow_up_required=False,
        human_review_required=False,
        merge_approved=True,
        completed_workers=["worker-1", "worker-2"],
        follow_up_workers=[],
        review_blockers=[],
        summary="Ralph accepted completed worker results.",
    )


def _lifecycle_decision() -> CodexGoalLifecycleDecisionResult:
    return CodexGoalLifecycleDecisionResult(
        goal_id="goal-restore",
        action="close_goal",
        next_target="goal_close",
        ready_to_close=True,
        requires_follow_up_wave=False,
        requires_human_approval=False,
        follow_up_workers=[],
        review_blockers=[],
        summary="Goal is ready to close.",
    )


def test_goal_lifecycle_artifact_store_round_trips_stage_bundle(tmp_path: Path) -> None:
    bundle = CodexGoalLifecycleArtifactBundle(
        goal_id="goal-restore",
        mirror_state=_mirror_state(),
        aggregation_report=_aggregation_report(),
        ralph_review_result=_ralph_review_result(),
        lifecycle_decision=_lifecycle_decision(),
    )
    store = CodexGoalLifecycleArtifactStore(working_directory=str(tmp_path))

    written_path = store.write_bundle(bundle)
    result = store.read_bundle("goal-restore")

    assert written_path == tmp_path / ".agent-remote" / "state" / "goal-lifecycle" / "goal-restore.json"
    assert result.goal_id == "goal-restore"
    assert result.aggregation_report is not None
    assert result.aggregation_report.completed_workers == ("worker-1", "worker-2")
    assert result.lifecycle_decision is not None
    assert result.lifecycle_decision.action == "close_goal"


def test_restore_goal_lifecycle_state_resumes_at_ralph_review_after_aggregation(tmp_path: Path) -> None:
    bundle = CodexGoalLifecycleArtifactBundle(
        goal_id="goal-restore",
        mirror_state=_mirror_state(),
        aggregation_report=_aggregation_report(),
    )
    CodexGoalLifecycleArtifactStore(working_directory=str(tmp_path)).write_bundle(bundle)

    result = restore_goal_lifecycle_state("goal-restore", working_directory=str(tmp_path))

    assert result.next_resume_target == "ralph_post_team_review"
    assert result.ready_to_resume is True
    assert result.bundle.aggregation_report is not None
    assert result.bundle.ralph_review_result is None


def test_restore_goal_lifecycle_state_resumes_at_goal_decision_after_ralph_review(tmp_path: Path) -> None:
    bundle = CodexGoalLifecycleArtifactBundle(
        goal_id="goal-restore",
        mirror_state=_mirror_state(),
        aggregation_report=_aggregation_report(),
        ralph_review_result=_ralph_review_result(),
    )
    CodexGoalLifecycleArtifactStore(working_directory=str(tmp_path)).write_bundle(bundle)

    result = restore_goal_lifecycle_state("goal-restore", working_directory=str(tmp_path))

    assert result.next_resume_target == "goal_lifecycle_decision"
    assert result.ready_to_resume is True


def test_restore_goal_lifecycle_state_uses_final_decision_target_when_present(tmp_path: Path) -> None:
    bundle = CodexGoalLifecycleArtifactBundle(
        goal_id="goal-restore",
        mirror_state=_mirror_state(),
        aggregation_report=_aggregation_report(),
        ralph_review_result=_ralph_review_result(),
        lifecycle_decision=_lifecycle_decision(),
    )
    CodexGoalLifecycleArtifactStore(working_directory=str(tmp_path)).write_bundle(bundle)

    result = restore_goal_lifecycle_state("goal-restore", working_directory=str(tmp_path))

    assert result.next_resume_target == "goal_close"
    assert result.ready_to_resume is True


def test_goal_lifecycle_artifact_bundle_rejects_mismatched_goal_id() -> None:
    with pytest.raises(ValueError, match="mirror_state goal_id must match bundle goal_id"):
        CodexGoalLifecycleArtifactBundle(
            goal_id="goal-restore",
            mirror_state=_mirror_state(goal_id="other-goal"),
        )


def test_get_goal_lifecycle_artifact_path_uses_agent_remote_state_directory(tmp_path: Path) -> None:
    result = get_goal_lifecycle_artifact_path("goal-restore", working_directory=str(tmp_path))

    assert result == tmp_path / ".agent-remote" / "state" / "goal-lifecycle" / "goal-restore.json"



def test_codex_goal_supervisor_exports_lifecycle_restore_surface(tmp_path: Path) -> None:
    bundle = CodexGoalLifecycleArtifactBundle(
        goal_id="goal-restore",
        mirror_state=_mirror_state(),
        aggregation_report=_aggregation_report(),
    )
    CodexGoalLifecycleArtifactStore(working_directory=str(tmp_path)).write_bundle(bundle)

    result = supervisor_restore_goal_lifecycle_state("goal-restore", working_directory=str(tmp_path))

    assert result.next_resume_target == "ralph_post_team_review"
