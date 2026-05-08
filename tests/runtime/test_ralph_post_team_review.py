from omx_remote.runtime.ralph.ralph_post_team_review import build_ralph_post_team_review
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewRequest
from omx_remote.schemas.teamwork.admin_aggregation_schemas import TeamAdminAggregationReport


def _assignment(worker_id: str, owned_file: str) -> dict[str, object]:
    return {
        "worker_id": worker_id,
        "lane_name": f"{worker_id} lane",
        "objective": f"Implement {worker_id} slice.",
        "owned_files": [owned_file],
        "tdd_steps": ["write failing test", "make it pass"],
        "verification_commands": ["uv run pytest -q"],
        "handoff_summary_required": "Summarize result and verification.",
        "authorization_policy": "llm_review",
        "authorization_scope": {
            "allowed_commands": ["uv run pytest -q"],
            "forbidden_commands": ["git push"],
            "requires_human_for": ["network mutation"],
            "requires_llm_review_for": ["code changes"],
        },
    }


def _prd_artifact() -> RalphPrdArtifact:
    return RalphPrdArtifact(
        objective="Ship a Team Admin review gate.",
        scope=["runtime/ralph", "schemas/ralph"],
        constraints=["Use typed contracts."],
        execution_plan=["Review Team Admin aggregation report."],
        verification_expectations=["uv run pytest -q"],
        requires_team_fanout=True,
        team_worker_count=2,
        continuation_policy="continue_automatically",
        team_worker_assignments=(
            _assignment("worker-1", "src/worker_one.py"),
            _assignment("worker-2", "src/worker_two.py"),
        ),
        team_admin={
            "admin_id": "team-admin",
            "aggregation_policy": "collect_all_workers_then_review",
            "merge_policy": "review_before_merge",
            "completion_policy": "all_required_tasks_completed",
            "requires_human_for": ["blocked_workers", "missing_workers"],
            "requires_llm_review_for": ["final_report"],
            "final_report_required": True,
        },
    )


def _aggregation_report(**overrides: object) -> TeamAdminAggregationReport:
    payload: dict[str, object] = {
        "admin_id": "team-admin",
        "aggregation_state": "ready_for_ralph_review",
        "merge_ready": True,
        "final_report_required": True,
        "completed_workers": ["worker-1", "worker-2"],
        "missing_workers": [],
        "blocked_workers": [],
        "incomplete_workers": [],
        "requires_human_review": False,
        "requires_llm_review": True,
        "task_count": 2,
        "event_count": 5,
        "summary": "Team Admin collected 2/2 completed worker results; ready for Ralph review.",
    }
    payload.update(overrides)
    return TeamAdminAggregationReport.model_validate(payload)


def test_ralph_post_team_review_marks_clean_report_complete() -> None:
    result = build_ralph_post_team_review(
        RalphPostTeamReviewRequest(
            ralph_prd_artifact=_prd_artifact(),
            aggregation_report=_aggregation_report(),
        )
    )

    assert result.decision == "complete"
    assert result.complete is True
    assert result.merge_approved is True
    assert result.follow_up_required is False
    assert result.human_review_required is False
    assert result.follow_up_workers == ()


def test_ralph_post_team_review_requires_follow_up_for_waiting_workers() -> None:
    result = build_ralph_post_team_review(
        RalphPostTeamReviewRequest(
            ralph_prd_artifact=_prd_artifact(),
            aggregation_report=_aggregation_report(
                aggregation_state="waiting_for_workers",
                merge_ready=False,
                completed_workers=["worker-1"],
                incomplete_workers=["worker-2"],
                summary="Team Admin is waiting for worker-2.",
            ),
        )
    )

    assert result.decision == "follow_up_wave_required"
    assert result.complete is False
    assert result.merge_approved is False
    assert result.follow_up_required is True
    assert result.human_review_required is False
    assert result.follow_up_workers == ("worker-2",)



def test_ralph_post_team_review_surfaces_startup_issue_for_follow_up() -> None:
    result = build_ralph_post_team_review(
        RalphPostTeamReviewRequest(
            ralph_prd_artifact=_prd_artifact(),
            aggregation_report=_aggregation_report(
                aggregation_state="waiting_for_workers",
                merge_ready=False,
                completed_workers=["worker-1"],
                startup_issue_workers=["worker-2"],
                incomplete_workers=["worker-2"],
                summary="Team Admin found a startup issue worker.",
            ),
        )
    )

    assert result.decision == "follow_up_wave_required"
    assert result.human_review_required is False
    assert result.follow_up_workers == ("worker-2",)
    assert result.startup_issue_workers == ("worker-2",)
    assert result.review_blockers == ()



def test_ralph_post_team_review_escalates_blocked_or_missing_workers() -> None:
    result = build_ralph_post_team_review(
        RalphPostTeamReviewRequest(
            ralph_prd_artifact=_prd_artifact(),
            aggregation_report=_aggregation_report(
                aggregation_state="human_review_required",
                merge_ready=False,
                completed_workers=["worker-1"],
                missing_workers=["worker-2"],
                incomplete_workers=["worker-2"],
                requires_human_review=True,
                summary="Team Admin found a missing worker.",
            ),
        )
    )

    assert result.decision == "human_review_required"
    assert result.human_review_required is True
    assert result.merge_approved is False
    assert result.review_blockers == ("worker-2",)


def test_ralph_post_team_review_rejects_report_that_conflicts_with_prd_workers() -> None:
    result = build_ralph_post_team_review(
        RalphPostTeamReviewRequest(
            ralph_prd_artifact=_prd_artifact(),
            aggregation_report=_aggregation_report(
                completed_workers=["worker-1"],
                summary="Team Admin incorrectly says merge is ready.",
            ),
        )
    )

    assert result.decision == "human_review_required"
    assert result.human_review_required is True
    assert result.merge_approved is False
    assert result.review_blockers == ("worker-2",)
