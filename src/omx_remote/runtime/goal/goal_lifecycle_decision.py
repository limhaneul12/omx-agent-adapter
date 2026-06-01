from omx_remote.schemas.codex_goal.lifecycle_schemas import (
    CodexGoalLifecycleDecisionRequest,
    CodexGoalLifecycleDecisionResult,
)
from omx_remote.shared.omx_enums.codex_goal_enums import (
    CodexGoalLifecycleAction,
    CodexGoalLifecycleTarget,
)
from omx_remote.shared.omx_enums.ralph_enums import RalphPostTeamReviewDecision


def build_goal_lifecycle_summary(
    request: CodexGoalLifecycleDecisionRequest,
    action: CodexGoalLifecycleAction,
) -> str:
    """Builds a stable Goal lifecycle decision summary.

    Args:
        request [CodexGoalLifecycleDecisionRequest]: Goal lifecycle decision request.
        action [CodexGoalLifecycleAction]: Selected lifecycle action.

    Returns:
        str: Agent-facing summary for the Goal control surface.
    """
    goal_id: str = request.mirror_state.goal_id
    if action == CodexGoalLifecycleAction.CLOSE_GOAL:
        summary = f"Goal {goal_id} is ready to close after Ralph approved Team results."
    elif action == CodexGoalLifecycleAction.PREPARE_FOLLOW_UP_WAVE:
        worker_count: int = len(request.ralph_review_result.follow_up_workers)
        summary = f"Goal {goal_id} needs a Ralph follow-up wave for {worker_count} worker result."
    else:
        blocker_count: int = len(request.ralph_review_result.review_blockers)
        summary = (
            f"Goal {goal_id} is waiting for human review on {blocker_count} blocker."
        )

    return summary


def build_goal_review_blockers(
    request: CodexGoalLifecycleDecisionRequest,
) -> tuple[str, ...]:
    """Builds Goal-level review blockers from Ralph's post-Team review result.

    Args:
        request [CodexGoalLifecycleDecisionRequest]: Goal lifecycle decision request.

    Returns:
        tuple[str, ...]: Review blockers that prevent Goal close or follow-up automation.
    """
    blockers: tuple[str, ...] = request.ralph_review_result.review_blockers
    if (
        request.ralph_review_result.decision == RalphPostTeamReviewDecision.COMPLETE
        and not request.ralph_review_result.merge_approved
    ):
        blockers = (*blockers, "merge_not_approved")

    result: tuple[str, ...] = blockers
    return result


def select_goal_lifecycle_action(
    request: CodexGoalLifecycleDecisionRequest,
) -> CodexGoalLifecycleAction:
    """Selects the Goal lifecycle action after Ralph post-Team review.

    Args:
        request [CodexGoalLifecycleDecisionRequest]: Goal lifecycle decision request.

    Returns:
        CodexGoalLifecycleAction: Goal close, follow-up wave, or human review action.
    """
    review_result = request.ralph_review_result
    has_goal_blocker: bool = bool(build_goal_review_blockers(request))
    if review_result.human_review_required or has_goal_blocker:
        action = CodexGoalLifecycleAction.WAIT_FOR_HUMAN_REVIEW
    elif review_result.decision == RalphPostTeamReviewDecision.FOLLOW_UP_WAVE_REQUIRED:
        action = CodexGoalLifecycleAction.PREPARE_FOLLOW_UP_WAVE
    elif review_result.complete and review_result.merge_approved:
        action = CodexGoalLifecycleAction.CLOSE_GOAL
    else:
        action = CodexGoalLifecycleAction.WAIT_FOR_HUMAN_REVIEW

    return action


def goal_lifecycle_target_for_action(
    action: CodexGoalLifecycleAction,
) -> CodexGoalLifecycleTarget:
    """Maps a Goal lifecycle action to the next adapter control target.

    Args:
        action [CodexGoalLifecycleAction]: Selected Goal lifecycle action.

    Returns:
        CodexGoalLifecycleTarget: Next target the adapter should expose to agents.
    """
    if action == CodexGoalLifecycleAction.CLOSE_GOAL:
        target = CodexGoalLifecycleTarget.GOAL_CLOSE
    elif action == CodexGoalLifecycleAction.PREPARE_FOLLOW_UP_WAVE:
        target = CodexGoalLifecycleTarget.RALPH_FOLLOW_UP
    else:
        target = CodexGoalLifecycleTarget.HUMAN_REVIEW

    return target


def build_goal_lifecycle_decision(
    request: CodexGoalLifecycleDecisionRequest,
) -> CodexGoalLifecycleDecisionResult:
    """Builds Goal close/follow-up/human-review decision from Ralph review output.

    Args:
        request [CodexGoalLifecycleDecisionRequest]: Typed lifecycle decision request.

    Returns:
        CodexGoalLifecycleDecisionResult: Goal-facing lifecycle action and next target.
    """
    action: CodexGoalLifecycleAction = select_goal_lifecycle_action(request)
    next_target: CodexGoalLifecycleTarget = goal_lifecycle_target_for_action(action)
    review_blockers: tuple[str, ...] = build_goal_review_blockers(request)
    ready_to_close: bool = action == CodexGoalLifecycleAction.CLOSE_GOAL
    requires_follow_up_wave: bool = (
        action == CodexGoalLifecycleAction.PREPARE_FOLLOW_UP_WAVE
    )
    requires_human_approval: bool = (
        action == CodexGoalLifecycleAction.WAIT_FOR_HUMAN_REVIEW
    )
    summary: str = build_goal_lifecycle_summary(request, action)
    decision = CodexGoalLifecycleDecisionResult(
        goal_id=request.mirror_state.goal_id,
        action=action,
        next_target=next_target,
        ready_to_close=ready_to_close,
        requires_follow_up_wave=requires_follow_up_wave,
        requires_human_approval=requires_human_approval,
        follow_up_workers=request.ralph_review_result.follow_up_workers,
        review_blockers=review_blockers,
        summary=summary,
    )
    return decision
