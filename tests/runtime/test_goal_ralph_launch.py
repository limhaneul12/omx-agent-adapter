from pathlib import Path

from omx_remote.runtime.goal.goal_ralph_launch import (
    build_goal_ralph_launch_request,
    prepare_goal_ralph_prd_review,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.shared.omx_enums.codex_goal_enums import GoalRalphPrdReviewMode
from omx_remote.shared.omx_enums.ralph_enums import RalphPrdContinuationPolicy


def _build_goal_mirror_state(tmp_path: Path) -> CodexGoalMirrorState:
    return CodexGoalMirrorState(
        goal_id="goal-review",
        objective_text="Add one reviewed Goal to Ralph pipeline slice.",
        source="codex_goal",
        execution_shape="ralph_pipeline",
        review_policy="review_required",
        team_worker_count=None,
        working_directory=str(tmp_path),
        codex_command=["codex", "--enable", "goals"],
        session_locator="agent-remote-goal-goal-review",
        process_id=1234,
        launched_at="2026-05-07T00:00:00+00:00",
        handoff_state="awaiting_ralph",
        tracking_state="active",
    )


def test_prepare_goal_ralph_prd_review_writes_typed_prd_and_llm_review_prompt(tmp_path: Path) -> None:
    mirror_state = _build_goal_mirror_state(tmp_path)
    request = build_goal_ralph_launch_request(
        mirror_state=mirror_state,
        source_paths=("AGENTS.md", "src/omx_remote/runtime/goal/"),
        requested_slice="Goal to Ralph one command bridge",
        constraints=("keep Ralph independently operable",),
        verification_expectations=("uv run pytest tests/runtime/test_goal_ralph_launch.py -q passes",),
        review_mode=GoalRalphPrdReviewMode.LLM_PROMPT,
        inherit_stdio=True,
        force_cleanup=True,
        allow_non_tty=False,
    )

    result = prepare_goal_ralph_prd_review(request)

    assert result.launch_attempted is False
    assert result.review_required is True
    assert result.review_prompt_path is not None
    assert result.review_prompt_path.endswith("goal-review-ralph-prd-review.md")
    assert result.prd_path.endswith(".omx/prd.json")
    assert result.ralph_prd_artifact.objective == mirror_state.objective_text
    assert result.ralph_prd_artifact.continuation_policy == RalphPrdContinuationPolicy.REVIEW_REQUIRED
    assert "LLM Ralph PRD Review" in Path(result.review_prompt_path).read_text()
    assert "Approve only if" in Path(result.review_prompt_path).read_text()


def test_prepare_goal_ralph_auto_approve_marks_prd_ready_without_review_prompt(tmp_path: Path) -> None:
    mirror_state = _build_goal_mirror_state(tmp_path)
    request = build_goal_ralph_launch_request(
        mirror_state=mirror_state,
        source_paths=("AGENTS.md",),
        requested_slice="Goal to Ralph one command bridge",
        constraints=(),
        verification_expectations=("targeted tests pass",),
        review_mode=GoalRalphPrdReviewMode.AUTO_APPROVE,
        inherit_stdio=False,
        force_cleanup=False,
        allow_non_tty=True,
    )

    result = prepare_goal_ralph_prd_review(request)

    assert result.review_required is False
    assert result.review_prompt_path is None
    assert result.ralph_prd_artifact.continuation_policy == RalphPrdContinuationPolicy.CONTINUE_AUTOMATICALLY
    assert Path(result.prd_path).exists()
