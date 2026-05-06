from omx_remote.runtime.goal.codex_goal_supervisor import (
    build_goal_lifecycle_decision as supervisor_build_goal_lifecycle_decision,
)
from omx_remote.runtime.goal.goal_lifecycle_decision import build_goal_lifecycle_decision
from omx_remote.schemas.codex_goal.lifecycle_schemas import CodexGoalLifecycleDecisionRequest
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult


def _mirror_state() -> CodexGoalMirrorState:
    return CodexGoalMirrorState(
        goal_id="goal-1",
        objective_text="Ship Team Admin review loop.",
        source="codex_goal",
        execution_shape="ralph_pipeline",
        review_policy="continue_automatically",
        team_worker_count=2,
        working_directory="/tmp/project",
        codex_command=["codex", "--enable", "goals"],
        session_locator="agent-remote-goal-goal-1",
        process_id=1234,
        launched_at="2026-05-05T12:00:00+00:00",
        handoff_state="ralph_started",
        tracking_state="active",
    )


def _ralph_review_result(**overrides: object) -> RalphPostTeamReviewResult:
    payload: dict[str, object] = {
        "decision": "complete",
        "complete": True,
        "follow_up_required": False,
        "human_review_required": False,
        "merge_approved": True,
        "completed_workers": ["worker-1", "worker-2"],
        "follow_up_workers": [],
        "review_blockers": [],
        "summary": "Ralph accepted completed worker results.",
    }
    payload.update(overrides)
    return RalphPostTeamReviewResult.model_validate(payload)


def test_goal_lifecycle_decision_closes_goal_after_complete_ralph_review() -> None:
    result = build_goal_lifecycle_decision(
        CodexGoalLifecycleDecisionRequest(
            mirror_state=_mirror_state(),
            ralph_review_result=_ralph_review_result(),
        )
    )

    assert result.goal_id == "goal-1"
    assert result.action == "close_goal"
    assert result.ready_to_close is True
    assert result.requires_follow_up_wave is False
    assert result.requires_human_approval is False
    assert result.next_target == "goal_close"
    assert result.follow_up_workers == ()


def test_goal_lifecycle_decision_requests_follow_up_wave_from_ralph_review() -> None:
    result = build_goal_lifecycle_decision(
        CodexGoalLifecycleDecisionRequest(
            mirror_state=_mirror_state(),
            ralph_review_result=_ralph_review_result(
                decision="follow_up_wave_required",
                complete=False,
                follow_up_required=True,
                merge_approved=False,
                follow_up_workers=["worker-2"],
                summary="Ralph found a follow-up worker.",
            ),
        )
    )

    assert result.action == "prepare_follow_up_wave"
    assert result.ready_to_close is False
    assert result.requires_follow_up_wave is True
    assert result.requires_human_approval is False
    assert result.next_target == "ralph_follow_up"
    assert result.follow_up_workers == ("worker-2",)


def test_goal_lifecycle_decision_waits_for_human_when_ralph_requires_review() -> None:
    result = build_goal_lifecycle_decision(
        CodexGoalLifecycleDecisionRequest(
            mirror_state=_mirror_state(),
            ralph_review_result=_ralph_review_result(
                decision="human_review_required",
                complete=False,
                human_review_required=True,
                merge_approved=False,
                review_blockers=["worker-2"],
                summary="Ralph requires human review.",
            ),
        )
    )

    assert result.action == "wait_for_human_review"
    assert result.ready_to_close is False
    assert result.requires_follow_up_wave is False
    assert result.requires_human_approval is True
    assert result.next_target == "human_review"
    assert result.review_blockers == ("worker-2",)


def test_goal_lifecycle_decision_blocks_complete_without_merge_approval() -> None:
    result = build_goal_lifecycle_decision(
        CodexGoalLifecycleDecisionRequest(
            mirror_state=_mirror_state(),
            ralph_review_result=_ralph_review_result(
                merge_approved=False,
                summary="Conflicting complete result should not close.",
            ),
        )
    )

    assert result.action == "wait_for_human_review"
    assert result.ready_to_close is False
    assert result.requires_human_approval is True
    assert result.review_blockers == ("merge_not_approved",)



def test_codex_goal_supervisor_exports_lifecycle_decision_surface() -> None:
    result = supervisor_build_goal_lifecycle_decision(
        CodexGoalLifecycleDecisionRequest(
            mirror_state=_mirror_state(),
            ralph_review_result=_ralph_review_result(),
        )
    )

    assert result.action == "close_goal"
