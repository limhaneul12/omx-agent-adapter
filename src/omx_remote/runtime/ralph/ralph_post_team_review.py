from omx_remote.schemas.ralph.review_schemas import (
    RalphPostTeamReviewRequest,
    RalphPostTeamReviewResult,
)
from omx_remote.shared.omx_enums.ralph_enums import RalphPostTeamReviewDecision
from omx_remote.shared.omx_enums.team_admin_enums import TeamAdminAggregationState


def expected_team_worker_ids(request: RalphPostTeamReviewRequest) -> tuple[str, ...]:
    """Extracts Ralph-assigned Team worker IDs from a post-Team review request.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        tuple[str, ...]: Worker IDs that Ralph expected Team Admin to aggregate.

    Raises:
        ValueError: Raised when the PRD does not contain Team worker assignments.
    """
    assignments = request.ralph_prd_artifact.team_worker_assignments
    if assignments is None:
        raise ValueError("Ralph post-Team review requires Team worker assignments.")

    worker_ids: tuple[str, ...] = tuple(assignment.worker_id for assignment in assignments)
    return worker_ids


def unique_ordered_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicates tokens while preserving first-seen order.

    Args:
        tokens [tuple[str, ...]]: Candidate review worker tokens.

    Returns:
        tuple[str, ...]: Stable first-seen ordered tokens without duplicates.
    """
    seen_tokens: set[str] = set()
    ordered_tokens: list[str] = []
    for token in tokens:
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        ordered_tokens.append(token)

    result: tuple[str, ...] = tuple(ordered_tokens)
    return result


def report_worker_tokens(request: RalphPostTeamReviewRequest) -> tuple[str, ...]:
    """Collects worker IDs named by the Team Admin aggregation report.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        tuple[str, ...]: Worker IDs mentioned by the aggregation report.
    """
    report = request.aggregation_report
    worker_tokens: tuple[str, ...] = unique_ordered_tokens(
        report.completed_workers
        + report.missing_workers
        + report.blocked_workers
        + report.incomplete_workers
    )
    return worker_tokens


def missing_expected_workers(request: RalphPostTeamReviewRequest) -> tuple[str, ...]:
    """Finds Ralph-assigned workers that are absent from the Team Admin report.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        tuple[str, ...]: Expected worker IDs missing from all report buckets.
    """
    expected_workers: tuple[str, ...] = expected_team_worker_ids(request)
    reported_workers: set[str] = set(report_worker_tokens(request))
    missing_workers: tuple[str, ...] = tuple(
        worker_id for worker_id in expected_workers if worker_id not in reported_workers
    )
    return missing_workers


def unexpected_report_workers(request: RalphPostTeamReviewRequest) -> tuple[str, ...]:
    """Finds Team Admin report workers that Ralph did not assign in the PRD.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        tuple[str, ...]: Reported worker IDs outside Ralph's assignment plan.
    """
    expected_workers: set[str] = set(expected_team_worker_ids(request))
    unexpected_workers: tuple[str, ...] = tuple(
        worker_id for worker_id in report_worker_tokens(request) if worker_id not in expected_workers
    )
    return unexpected_workers


def build_review_blockers(request: RalphPostTeamReviewRequest) -> tuple[str, ...]:
    """Builds the worker blocker set for Ralph post-Team review.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        tuple[str, ...]: Worker IDs that block merge approval or completion.
    """
    report = request.aggregation_report
    blockers: tuple[str, ...] = unique_ordered_tokens(
        report.blocked_workers
        + report.missing_workers
        + missing_expected_workers(request)
        + unexpected_report_workers(request)
    )
    return blockers


def build_follow_up_workers(request: RalphPostTeamReviewRequest) -> tuple[str, ...]:
    """Builds the Team worker list for a follow-up Ralph wave.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        tuple[str, ...]: Worker IDs that should receive follow-up assignment.
    """
    report = request.aggregation_report
    workers: tuple[str, ...] = unique_ordered_tokens(
        report.incomplete_workers + report.missing_workers + missing_expected_workers(request)
    )
    return workers


def report_conflicts_with_prd(request: RalphPostTeamReviewRequest) -> bool:
    """Checks whether Team Admin report buckets conflict with Ralph's PRD.

    Args:
        request [RalphPostTeamReviewRequest]: Ralph post-Team review request.

    Returns:
        bool: True when report worker coverage or admin identity conflicts with the PRD.
    """
    team_admin = request.ralph_prd_artifact.team_admin
    admin_id_mismatch: bool = bool(
        team_admin is not None and request.aggregation_report.admin_id != team_admin.admin_id
    )
    has_worker_conflict: bool = bool(
        missing_expected_workers(request) or unexpected_report_workers(request)
    )
    conflicts: bool = admin_id_mismatch or has_worker_conflict
    return conflicts


def build_ralph_post_team_review_summary(
    decision: RalphPostTeamReviewDecision,
    completed_workers: tuple[str, ...],
    follow_up_workers: tuple[str, ...],
    review_blockers: tuple[str, ...],
) -> str:
    """Builds a stable Ralph post-Team review summary.

    Args:
        decision [RalphPostTeamReviewDecision]: Final Ralph post-Team review decision.
        completed_workers [tuple[str, ...]]: Workers accepted as complete by Ralph.
        follow_up_workers [tuple[str, ...]]: Workers needing follow-up assignment.
        review_blockers [tuple[str, ...]]: Workers requiring human review.

    Returns:
        str: Goal-facing summary of Ralph's post-Team review decision.
    """
    if decision == RalphPostTeamReviewDecision.COMPLETE:
        summary = (
            f"Ralph accepted {len(completed_workers)} completed worker results; "
            "Goal may close or proceed to final verification."
        )
    elif decision == RalphPostTeamReviewDecision.FOLLOW_UP_WAVE_REQUIRED:
        summary = (
            f"Ralph found {len(follow_up_workers)} worker result needing follow-up; "
            "Goal should schedule another Team wave."
        )
    else:
        summary = (
            f"Ralph found {len(review_blockers)} post-Team review blocker; "
            "human review is required before merge or follow-up."
        )

    return summary


def build_ralph_post_team_review(
    request: RalphPostTeamReviewRequest,
) -> RalphPostTeamReviewResult:
    """Reviews Team Admin aggregation against a Ralph PRD.

    Args:
        request [RalphPostTeamReviewRequest]: Typed Ralph post-Team review request.

    Returns:
        RalphPostTeamReviewResult: Goal-facing review decision for complete/follow-up/human escalation.
    """
    report = request.aggregation_report
    review_blockers: tuple[str, ...] = build_review_blockers(request)
    follow_up_workers: tuple[str, ...] = build_follow_up_workers(request)
    has_report_conflict: bool = report_conflicts_with_prd(request)
    requires_human_review: bool = bool(
        report.requires_human_review
        or report.aggregation_state == TeamAdminAggregationState.HUMAN_REVIEW_REQUIRED
        or review_blockers
        or has_report_conflict
    )

    if requires_human_review:
        decision = RalphPostTeamReviewDecision.HUMAN_REVIEW_REQUIRED
    elif not report.merge_ready or report.incomplete_workers:
        decision = RalphPostTeamReviewDecision.FOLLOW_UP_WAVE_REQUIRED
    else:
        decision = RalphPostTeamReviewDecision.COMPLETE

    complete: bool = decision == RalphPostTeamReviewDecision.COMPLETE
    follow_up_required: bool = decision == RalphPostTeamReviewDecision.FOLLOW_UP_WAVE_REQUIRED
    merge_approved: bool = complete and report.merge_ready
    summary: str = build_ralph_post_team_review_summary(
        decision,
        report.completed_workers,
        follow_up_workers,
        review_blockers,
    )
    result: RalphPostTeamReviewResult = RalphPostTeamReviewResult.model_validate(
        {
            "decision": decision,
            "complete": complete,
            "follow_up_required": follow_up_required,
            "human_review_required": requires_human_review,
            "merge_approved": merge_approved,
            "completed_workers": report.completed_workers,
            "follow_up_workers": follow_up_workers,
            "review_blockers": review_blockers,
            "summary": summary,
        }
    )
    return result
