from omx_remote.runtime.goal.codex_goal_supervisor import (
    build_goal_operating_decision as supervisor_build_goal_operating_decision,
)
from omx_remote.runtime.goal.goal_operating_decision import build_goal_operating_decision
from omx_remote.schemas.codex_goal.lifecycle_schemas import (
    CodexGoalLifecycleArtifactBundle,
    CodexGoalLifecycleDecisionResult,
    CodexGoalLifecycleRestoredState,
)
from omx_remote.schemas.codex_goal.operating_schemas import CodexGoalOperatingDecisionRequest
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult
from omx_remote.schemas.teamwork.admin_aggregation_schemas import TeamAdminAggregationReport


def _mirror_state(goal_id: str = "goal-operating") -> CodexGoalMirrorState:
    return CodexGoalMirrorState(
        goal_id=goal_id,
        objective_text="Operate OMX through Ralph and Team safely.",
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
        event_count=4,
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


def _lifecycle_decision(
    action: str = "close_goal",
    next_target: str = "goal_close",
    ready_to_close: bool = True,
    requires_follow_up_wave: bool = False,
    requires_human_approval: bool = False,
) -> CodexGoalLifecycleDecisionResult:
    return CodexGoalLifecycleDecisionResult(
        goal_id="goal-operating",
        action=action,
        next_target=next_target,
        ready_to_close=ready_to_close,
        requires_follow_up_wave=requires_follow_up_wave,
        requires_human_approval=requires_human_approval,
        follow_up_workers=["worker-2"] if requires_follow_up_wave else [],
        review_blockers=["worker-2"] if requires_human_approval else [],
        summary="Goal lifecycle decision is ready.",
    )


def _restored_state(
    next_resume_target: str,
    aggregation_report: TeamAdminAggregationReport | None = None,
    ralph_review_result: RalphPostTeamReviewResult | None = None,
    lifecycle_decision: CodexGoalLifecycleDecisionResult | None = None,
) -> CodexGoalLifecycleRestoredState:
    bundle = CodexGoalLifecycleArtifactBundle(
        goal_id="goal-operating",
        mirror_state=_mirror_state(),
        aggregation_report=aggregation_report,
        ralph_review_result=ralph_review_result,
        lifecycle_decision=lifecycle_decision,
    )
    return CodexGoalLifecycleRestoredState(
        artifact_path="/tmp/project/.agent-remote/state/goal-lifecycle/goal-operating.json",
        bundle=bundle,
        next_resume_target=next_resume_target,
        ready_to_resume=True,
        summary="Goal restored.",
    )


def test_goal_operating_decision_collects_team_admin_evidence_before_review() -> None:
    result = build_goal_operating_decision(
        CodexGoalOperatingDecisionRequest(
            restored_state=_restored_state("team_admin_aggregation"),
            team_name="team-alpha",
        )
    )

    assert result.current_stage == "team_admin_aggregation_pending"
    assert result.next_action == "collect_team_admin_aggregation"
    assert result.safe_to_mutate is False
    assert result.requires_review is False
    assert result.missing_evidence == (
        "omx_team_api_list_tasks",
        "omx_team_api_read_events",
        "omx_team_api_read_worker_status",
    )
    assert result.recommended_commands == (
        "omx team api list-tasks --input '{\"team_name\":\"team-alpha\"}' --json",
        "omx team api read-events --input '{\"team_name\":\"team-alpha\"}' --json",
        "omx team api read-worker-status --input '{\"team_name\":\"team-alpha\",\"worker\":\"worker-1\"}' --json",
        "omx team api read-worker-status --input '{\"team_name\":\"team-alpha\",\"worker\":\"worker-2\"}' --json",
    )


def test_goal_operating_decision_runs_ralph_review_after_aggregation_artifact() -> None:
    result = build_goal_operating_decision(
        CodexGoalOperatingDecisionRequest(
            restored_state=_restored_state(
                "ralph_post_team_review",
                aggregation_report=_aggregation_report(),
            ),
            team_name="team-alpha",
        )
    )

    assert result.current_stage == "ralph_post_team_review_pending"
    assert result.next_action == "run_ralph_post_team_review"
    assert result.available_evidence == ("goal_lifecycle_artifact", "team_admin_aggregation_report")
    assert result.missing_evidence == ()
    assert result.safe_to_mutate is False


def test_goal_operating_decision_builds_lifecycle_decision_after_ralph_review() -> None:
    result = build_goal_operating_decision(
        CodexGoalOperatingDecisionRequest(
            restored_state=_restored_state(
                "goal_lifecycle_decision",
                aggregation_report=_aggregation_report(),
                ralph_review_result=_ralph_review_result(),
            ),
            team_name="team-alpha",
        )
    )

    assert result.current_stage == "goal_lifecycle_decision_pending"
    assert result.next_action == "build_goal_lifecycle_decision"
    assert result.available_evidence == (
        "goal_lifecycle_artifact",
        "team_admin_aggregation_report",
        "ralph_post_team_review_result",
    )
    assert result.safe_to_mutate is False


def test_goal_operating_decision_allows_close_only_after_complete_lifecycle_decision() -> None:
    result = build_goal_operating_decision(
        CodexGoalOperatingDecisionRequest(
            restored_state=_restored_state(
                "goal_close",
                aggregation_report=_aggregation_report(),
                ralph_review_result=_ralph_review_result(),
                lifecycle_decision=_lifecycle_decision(),
            ),
            team_name="team-alpha",
        )
    )

    assert result.current_stage == "goal_close_ready"
    assert result.next_action == "close_goal"
    assert result.safe_to_mutate is True
    assert result.requires_review is False
    assert result.missing_evidence == ()


def test_goal_operating_decision_blocks_mutation_for_human_review_target() -> None:
    result = build_goal_operating_decision(
        CodexGoalOperatingDecisionRequest(
            restored_state=_restored_state(
                "human_review",
                aggregation_report=_aggregation_report(),
                ralph_review_result=_ralph_review_result(),
                lifecycle_decision=_lifecycle_decision(
                    action="wait_for_human_review",
                    next_target="human_review",
                    ready_to_close=False,
                    requires_human_approval=True,
                ),
            ),
            team_name="team-alpha",
        )
    )

    assert result.current_stage == "human_review_required"
    assert result.next_action == "wait_for_human_review"
    assert result.safe_to_mutate is False
    assert result.requires_review is True
    assert result.review_blockers == ("worker-2",)


def test_codex_goal_supervisor_exports_operating_decision_surface() -> None:
    result = supervisor_build_goal_operating_decision(
        CodexGoalOperatingDecisionRequest(
            restored_state=_restored_state("team_admin_aggregation"),
            team_name="team-alpha",
        )
    )

    assert result.next_action == "collect_team_admin_aggregation"
