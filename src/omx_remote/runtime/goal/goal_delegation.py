from omx_remote.runtime.goal.codex_goal_runtime import mark_codex_goal_handoff_started
from omx_remote.runtime.operators.operator_loop import (
    operate_ralph_launch,
    operate_ralph_resume,
    operate_ralph_team_launch,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalReviewPolicy
from omx_remote.schemas.codex_goal.supervisor_schemas import (
    GoalDelegationDecision,
    GoalDelegationDispatchAction,
    GoalDelegationDispatchResult,
    GoalDelegationDispatchStatus,
    GoalDelegationTarget,
    GoalExecutionPolicy,
)
from omx_remote.schemas.multi_operator.snapshot_schemas import (
    ManagedFlowKind,
    ManagedOmxFlow,
    MultiOperatorSnapshot,
)
from omx_remote.schemas.operator.action_schemas import OperatorActionResult
from omx_remote.schemas.ralph.prd_schemas import (
    RalphPrdArtifact,
    RalphPrdContinuationPolicy,
)


def _has_team_flow(multi_operator_snapshot: MultiOperatorSnapshot) -> bool:
    """Handles has team flow.
    
    Args:
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
    
    Returns:
        bool: Function return value.
    """
    has_team_flow: bool = any(
        flow.flow_kind == ManagedFlowKind.TEAM for flow in multi_operator_snapshot.flows.root
    )
    return has_team_flow



def _normalize_goal_objective_text(goal_objective_text: str) -> str:
    """Handles normalize goal objective text.
    
    Args:
        goal_objective_text [str]: Function argument.
    
    Returns:
        str: Function return value.
    """
    normalized_goal_objective_text: str = goal_objective_text.strip().lower()
    return normalized_goal_objective_text



def _ralph_prd_matches_goal_objective(
    goal_objective_text: str,
    ralph_prd_artifact: RalphPrdArtifact,
) -> bool:
    """Handles ralph prd matches goal objective.
    
    Args:
        goal_objective_text [str]: Function argument.
        ralph_prd_artifact [RalphPrdArtifact]: Function argument.
    
    Returns:
        bool: Function return value.
    """
    normalized_goal_objective_text: str = _normalize_goal_objective_text(
        goal_objective_text
    )
    normalized_prd_objective_text: str = _normalize_goal_objective_text(
        ralph_prd_artifact.objective
    )
    objectives_match: bool = normalized_goal_objective_text == normalized_prd_objective_text
    return objectives_match



def _find_tracked_ralph_flow(
    multi_operator_snapshot: MultiOperatorSnapshot,
) -> ManagedOmxFlow | None:
    """Handles find tracked ralph flow.
    
    Args:
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
    
    Returns:
        ManagedOmxFlow | None: Function return value.
    """
    tracked_ralph_flow: ManagedOmxFlow | None = None

    flow: ManagedOmxFlow
    for flow in multi_operator_snapshot.flows.root:
        if flow.flow_kind != ManagedFlowKind.RALPH:
            continue

        tracked_ralph_flow = flow
        break

    return tracked_ralph_flow



def _ralph_flow_requires_cleanup(
    multi_operator_snapshot: MultiOperatorSnapshot,
) -> bool:
    """Handles ralph flow requires cleanup.
    
    Args:
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
    
    Returns:
        bool: Function return value.
    """
    tracked_ralph_flow: ManagedOmxFlow | None = _find_tracked_ralph_flow(
        multi_operator_snapshot
    )
    if tracked_ralph_flow is None:
        requires_cleanup: bool = False
        return requires_cleanup

    requires_cleanup = tracked_ralph_flow.flow_id in multi_operator_snapshot.cleanup_flow_ids
    return requires_cleanup



def _ralph_flow_is_resumable(
    multi_operator_snapshot: MultiOperatorSnapshot,
) -> bool:
    """Handles ralph flow is resumable.
    
    Args:
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
    
    Returns:
        bool: Function return value.
    """
    tracked_ralph_flow: ManagedOmxFlow | None = _find_tracked_ralph_flow(
        multi_operator_snapshot
    )
    if tracked_ralph_flow is None:
        is_resumable: bool = False
        return is_resumable

    is_resumable = tracked_ralph_flow.flow_id in multi_operator_snapshot.resumable_flow_ids
    return is_resumable



def _apply_native_goal_review_policy(
    execution_policy: GoalExecutionPolicy,
    review_policy: CodexGoalReviewPolicy,
) -> GoalExecutionPolicy:
    """Handles apply native goal review policy.
    
    Args:
        execution_policy [GoalExecutionPolicy]: Function argument.
        review_policy [CodexGoalReviewPolicy]: Function argument.
    
    Returns:
        GoalExecutionPolicy: Function return value.
    """
    if review_policy != CodexGoalReviewPolicy.REVIEW_REQUIRED:
        return execution_policy

    updated_execution_policy: GoalExecutionPolicy = execution_policy.model_copy(
        update={"prds_require_review_before_execution": True}
    )
    return updated_execution_policy


def select_goal_delegation(
    goal_id: str,
    multi_operator_snapshot: MultiOperatorSnapshot,
    execution_policy: GoalExecutionPolicy,
    objective_is_already_structured: bool,
    requires_parallel_fanout: bool,
    goal_should_remain_standalone: bool,
    requested_team_worker_count: int | None = None,
    goal_objective_text: str | None = None,
    ralph_prd_artifact: RalphPrdArtifact | None = None,
) -> GoalDelegationDecision:
    """Handles select goal delegation.
    
    Args:
        goal_id [str]: Function argument.
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
        execution_policy [GoalExecutionPolicy]: Function argument.
        objective_is_already_structured [bool]: Function argument.
        requires_parallel_fanout [bool]: Function argument.
        goal_should_remain_standalone [bool]: Function argument.
        requested_team_worker_count [int | None]: Function argument.
        goal_objective_text [str | None]: Function argument.
        ralph_prd_artifact [RalphPrdArtifact | None]: Function argument.
    
    Returns:
        GoalDelegationDecision: Function return value.
    """
    if (
        execution_policy.prefer_observe_when_active_flow_exists
        and len(multi_operator_snapshot.active_flow_ids.root) > 0
    ):
        observe_only_decision: GoalDelegationDecision = GoalDelegationDecision(
            goal_id=goal_id,
            selected_target=GoalDelegationTarget.OBSERVE_ONLY,
            reason="an active tracked flow already exists, so observation is the safest next step",
        )
        return observe_only_decision

    if goal_should_remain_standalone and execution_policy.allow_goal_standalone:
        goal_only_decision: GoalDelegationDecision = GoalDelegationDecision(
            goal_id=goal_id,
            selected_target=GoalDelegationTarget.GOAL_ONLY,
            reason="the goal should remain tracked without delegating into OMX runtime flows yet",
        )
        return goal_only_decision

    if not execution_policy.allow_ralph_pipeline:
        if execution_policy.allow_direct_exec:
            plain_exec_decision: GoalDelegationDecision = GoalDelegationDecision(
                goal_id=goal_id,
                selected_target=GoalDelegationTarget.PLAIN_EXEC,
                reason="the Ralph pipeline is disabled, so plain execution is the remaining direct option",
            )
            return plain_exec_decision

        fallback_goal_only_decision: GoalDelegationDecision = GoalDelegationDecision(
            goal_id=goal_id,
            selected_target=GoalDelegationTarget.GOAL_ONLY,
            reason="the Ralph pipeline is disabled, so the goal stays tracked without delegation",
        )
        return fallback_goal_only_decision

    has_team_flow: bool = _has_team_flow(multi_operator_snapshot)
    requires_prd_refresh: bool
    requires_prd_review: bool
    requires_team_fanout: bool
    team_worker_count: int | None

    if goal_objective_text is None:
        requires_prd_refresh = not objective_is_already_structured
        requires_prd_review = execution_policy.prds_require_review_before_execution
        requires_team_fanout = requires_parallel_fanout and has_team_flow
        if requires_team_fanout:
            team_worker_count = requested_team_worker_count
        else:
            team_worker_count = None
    elif ralph_prd_artifact is None:
        requires_prd_refresh = True
        requires_prd_review = execution_policy.prds_require_review_before_execution
        requires_team_fanout = requires_parallel_fanout and has_team_flow
        if requires_team_fanout:
            team_worker_count = requested_team_worker_count
        else:
            team_worker_count = None
    else:
        has_matching_prd_artifact: bool = _ralph_prd_matches_goal_objective(
            goal_objective_text=goal_objective_text,
            ralph_prd_artifact=ralph_prd_artifact,
        )
        requires_prd_refresh = not has_matching_prd_artifact
        requires_prd_review = (
            execution_policy.prds_require_review_before_execution
            or ralph_prd_artifact.continuation_policy
            == RalphPrdContinuationPolicy.REVIEW_REQUIRED
        )
        artifact_requests_team_fanout: bool = ralph_prd_artifact.requires_team_fanout
        if has_matching_prd_artifact:
            requires_team_fanout = artifact_requests_team_fanout and has_team_flow
            if requires_team_fanout:
                team_worker_count = ralph_prd_artifact.team_worker_count
            else:
                team_worker_count = None
        else:
            requires_team_fanout = requires_parallel_fanout and has_team_flow
            if requires_team_fanout:
                team_worker_count = requested_team_worker_count
            else:
                team_worker_count = None

    can_finish_without_team: bool = not requires_team_fanout

    ralph_reason: str
    if requires_prd_refresh:
        ralph_reason = (
            "the goal needs Ralph to refresh a typed PRD artifact before execution proceeds"
        )
    elif requires_team_fanout:
        ralph_reason = (
            "the goal already has a matching Ralph PRD artifact and should continue into Team fanout"
        )
    elif can_finish_without_team:
        ralph_reason = (
            "the goal already has a matching Ralph PRD artifact and can continue without Team fanout"
        )
    else:
        ralph_reason = "the goal should proceed through the Ralph pipeline"

    ralph_pipeline_decision: GoalDelegationDecision = GoalDelegationDecision(
        goal_id=goal_id,
        selected_target=GoalDelegationTarget.RALPH_PIPELINE,
        reason=ralph_reason,
        requires_prd_refresh=requires_prd_refresh,
        requires_prd_review=requires_prd_review,
        requires_team_fanout=requires_team_fanout,
        team_worker_count=team_worker_count,
        can_finish_without_team=can_finish_without_team,
    )
    return ralph_pipeline_decision



def dispatch_goal_delegation(
    decision: GoalDelegationDecision,
    multi_operator_snapshot: MultiOperatorSnapshot,
    goal_objective_text: str,
    force_cleanup: bool,
    allow_non_tty: bool,
    goal_working_directory: str | None = None,
) -> GoalDelegationDispatchResult:
    """Handles dispatch goal delegation.
    
    Args:
        decision [GoalDelegationDecision]: Function argument.
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
        goal_objective_text [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
        goal_working_directory [str | None]: Function argument.
    
    Returns:
        GoalDelegationDispatchResult: Function return value.
    """
    if decision.selected_target != GoalDelegationTarget.RALPH_PIPELINE:
        not_applicable_result: GoalDelegationDispatchResult = GoalDelegationDispatchResult(
            goal_id=decision.goal_id,
            selected_target=decision.selected_target,
            dispatch_status=GoalDelegationDispatchStatus.NOT_APPLICABLE,
        )
        return not_applicable_result

    if decision.requires_prd_refresh:
        blocked_refresh_result: GoalDelegationDispatchResult = GoalDelegationDispatchResult(
            goal_id=decision.goal_id,
            selected_target=decision.selected_target,
            dispatch_status=GoalDelegationDispatchStatus.BLOCKED,
            blocker_reason="the goal still requires Ralph PRD refresh before dispatch",
        )
        return blocked_refresh_result

    if decision.requires_prd_review:
        blocked_review_result: GoalDelegationDispatchResult = GoalDelegationDispatchResult(
            goal_id=decision.goal_id,
            selected_target=decision.selected_target,
            dispatch_status=GoalDelegationDispatchStatus.BLOCKED,
            blocker_reason="the goal still requires Ralph PRD review before dispatch",
        )
        return blocked_review_result

    if _ralph_flow_requires_cleanup(multi_operator_snapshot):
        blocked_cleanup_result: GoalDelegationDispatchResult = GoalDelegationDispatchResult(
            goal_id=decision.goal_id,
            selected_target=decision.selected_target,
            dispatch_status=GoalDelegationDispatchStatus.BLOCKED,
            blocker_reason="the tracked Ralph flow requires cleanup before Goal can dispatch it",
        )
        return blocked_cleanup_result

    operator_result: OperatorActionResult
    dispatched_action: str
    if _ralph_flow_is_resumable(multi_operator_snapshot):
        operator_result = operate_ralph_resume()
        dispatched_action = GoalDelegationDispatchAction.RALPH_RESUME
    elif decision.requires_team_fanout:
        operator_result = operate_ralph_team_launch(allow_non_tty=allow_non_tty)
        dispatched_action = GoalDelegationDispatchAction.TEAM_LAUNCH
    else:
        operator_result = operate_ralph_launch(
            goal_objective_text,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
        )
        dispatched_action = GoalDelegationDispatchAction.RALPH_LAUNCH

    if goal_working_directory is not None:
        mark_codex_goal_handoff_started(
            goal_id=decision.goal_id,
            working_directory=goal_working_directory,
        )

    dispatched_result: GoalDelegationDispatchResult = GoalDelegationDispatchResult(
        goal_id=decision.goal_id,
        selected_target=decision.selected_target,
        dispatch_status=GoalDelegationDispatchStatus.DISPATCHED,
        dispatched_action=dispatched_action,
        operator_result=operator_result,
    )
    return dispatched_result
