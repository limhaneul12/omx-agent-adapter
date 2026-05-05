from omx_remote.runtime.codex_goal_runtime import (
    mark_codex_goal_handoff_started,
    read_codex_goal_status,
)
from omx_remote.runtime.operator_loop import (
    operate_ralph_launch,
    operate_ralph_resume,
    operate_ralph_team_launch,
)
from omx_remote.schemas.codex_goal import (
    CodexGoalAdvanceRequest,
    CodexGoalAdvanceResult,
    CodexGoalCapabilitySnapshot,
    CodexGoalExecutionShape,
    CodexGoalMirrorState,
    CodexGoalReviewPolicy,
    CodexGoalSnapshot,
    CodexGoalSource,
    CodexGoalStatus,
    GoalDelegationDecision,
    GoalDelegationDispatchAction,
    GoalDelegationDispatchResult,
    GoalDelegationDispatchStatus,
    GoalDelegationTarget,
    GoalExecutionPolicy,
    GoalToRalphHandoffPromptRequest,
    GoalToRalphHandoffPromptResult,
)
from omx_remote.schemas.multi_operator import (
    ManagedFlowKind,
    ManagedOmxFlow,
    MultiOperatorSnapshot,
)
from omx_remote.schemas.operator import OperatorActionResult, OperatorLoopState
from omx_remote.schemas.ralph import (
    RalphPrdArtifact,
    RalphPrdContinuationPolicy,
)

_BLOCKING_LOOP_STATES: frozenset[OperatorLoopState] = frozenset(
    {
        OperatorLoopState.TERMINAL_FAILURE,
        OperatorLoopState.STALE_STATE_FAILURE,
        OperatorLoopState.DIRTY_WORKSPACE_FAILURE,
        OperatorLoopState.BLOCKED_APPROVAL_NEEDED,
    }
)



def _build_open_blockers(multi_operator_snapshot: MultiOperatorSnapshot) -> list[str]:
    open_blockers: list[str] = []

    flow: ManagedOmxFlow
    for flow in multi_operator_snapshot.flows.root:
        flow_result: OperatorActionResult | None = flow.last_result
        if flow_result is None:
            continue

        if flow_result.loop_state not in _BLOCKING_LOOP_STATES:
            continue

        blocker_text = f"{flow.flow_id}: {flow_result.summary}"
        open_blockers.append(blocker_text)

    return open_blockers



def build_codex_goal_snapshot(
    *,
    goal_id: str,
    objective_text: str,
    capability: CodexGoalCapabilitySnapshot,
    multi_operator_snapshot: MultiOperatorSnapshot,
) -> CodexGoalSnapshot:
    tracked_flow_ids: list[str] = [flow.flow_id for flow in multi_operator_snapshot.flows.root]
    active_flow_ids: list[str] = list(multi_operator_snapshot.active_flow_ids.root)
    open_blockers: list[str] = _build_open_blockers(multi_operator_snapshot)

    result: CodexGoalSnapshot = CodexGoalSnapshot(
        goal_id=goal_id,
        objective_text=objective_text,
        status=CodexGoalStatus.ACTIVE,
        source=CodexGoalSource.ADAPTER_SUPERVISOR,
        capability=capability,
        tracked_flow_ids=tracked_flow_ids,
        active_flow_ids=active_flow_ids,
        open_blockers=open_blockers,
    )
    return result



def _has_team_flow(multi_operator_snapshot: MultiOperatorSnapshot) -> bool:
    has_team_flow: bool = any(
        flow.flow_kind == ManagedFlowKind.TEAM for flow in multi_operator_snapshot.flows.root
    )
    return has_team_flow



def _normalize_goal_objective_text(goal_objective_text: str) -> str:
    normalized_goal_objective_text: str = goal_objective_text.strip().lower()
    return normalized_goal_objective_text



def _ralph_prd_matches_goal_objective(
    *,
    goal_objective_text: str,
    ralph_prd_artifact: RalphPrdArtifact,
) -> bool:
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
    tracked_ralph_flow: ManagedOmxFlow | None = _find_tracked_ralph_flow(
        multi_operator_snapshot
    )
    if tracked_ralph_flow is None:
        is_resumable: bool = False
        return is_resumable

    is_resumable = tracked_ralph_flow.flow_id in multi_operator_snapshot.resumable_flow_ids
    return is_resumable



def _apply_native_goal_review_policy(
    *,
    execution_policy: GoalExecutionPolicy,
    review_policy: CodexGoalReviewPolicy,
) -> GoalExecutionPolicy:
    if review_policy != CodexGoalReviewPolicy.REVIEW_REQUIRED:
        return execution_policy

    updated_execution_policy: GoalExecutionPolicy = execution_policy.model_copy(
        update={"prds_require_review_before_execution": True}
    )
    return updated_execution_policy



def _format_handoff_bullets(values: tuple[str, ...]) -> str:
    bullet_lines: list[str] = [f"- {value}" for value in values]
    formatted_bullets: str = "\n".join(bullet_lines)
    return formatted_bullets



def _format_review_instruction(review_policy: CodexGoalReviewPolicy) -> str:
    if review_policy == CodexGoalReviewPolicy.REVIEW_REQUIRED:
        review_instruction: str = (
            "Stop after creating or validating the PRD artifact and wait for review."
        )
        return review_instruction

    review_instruction = (
        "After creating or validating the PRD artifact, report whether the artifact is ready for the next supervised advance."
    )
    return review_instruction



def _format_team_worker_count(team_worker_count: int | None) -> str:
    if team_worker_count is None:
        formatted_worker_count: str = "team_worker_count: not requested"
        return formatted_worker_count

    formatted_worker_count = f"team_worker_count: {team_worker_count}"
    return formatted_worker_count



def build_goal_to_ralph_handoff_prompt(
    request: GoalToRalphHandoffPromptRequest,
) -> str:
    """Render the Ralph PRD handoff prompt for a tracked Codex Goal.

    Args:
        request [GoalToRalphHandoffPromptRequest]: Typed Goal-to-Ralph handoff data.

    Returns:
        str: Prompt text Ralph can use to create or validate the PRD artifact.
    """
    source_path_lines: str = _format_handoff_bullets(request.source_paths)
    constraint_lines: str = _format_handoff_bullets(request.constraints)
    verification_lines: str = _format_handoff_bullets(request.verification_expectations)
    review_instruction: str = _format_review_instruction(request.review_policy)
    team_worker_count_line: str = _format_team_worker_count(request.team_worker_count)

    prompt: str = f"""You are Ralph, the PRD and execution-structuring operator for this repo.

Goal ID: {request.goal_id}

Goal objective:
{request.goal_objective_text}

Requested slice:
{request.requested_slice}

Source of truth:
{source_path_lines}

Constraints:
{constraint_lines}

Verification expectations:
{verification_lines}

Task:
Create or validate `.omx/prd.json` as a RalphPrdArtifact for the requested slice only.

The RalphPrdArtifact must include:
- objective
- scope
- constraints
- execution_plan
- verification_expectations
- requires_team_fanout
- team_worker_count when Team fanout is required
- continuation_policy

Pipeline policy:
- Preserve Ralph and Team as independently operable modes.
- Do not implement code from this handoff prompt.
- Do not launch Team from this handoff prompt.
- {team_worker_count_line}
- {review_instruction}
""".strip()
    return prompt



def prepare_tracked_codex_goal_ralph_handoff_prompt(
    *,
    source_paths: tuple[str, ...],
    requested_slice: str,
    constraints: tuple[str, ...],
    verification_expectations: tuple[str, ...],
    working_directory: str | None = None,
) -> GoalToRalphHandoffPromptResult:
    """Prepare a read-only Ralph PRD handoff prompt from tracked Goal mirror state.

    Args:
        source_paths [tuple[str, ...]]: Source-of-truth files or directories Ralph must read.
        requested_slice [str]: One implementation slice Ralph should structure.
        constraints [tuple[str, ...]]: Handoff constraints Ralph must preserve.
        verification_expectations [tuple[str, ...]]: Verification gates Ralph must include.
        working_directory [str | None]: Optional workspace whose Goal mirror state should be read.

    Returns:
        GoalToRalphHandoffPromptResult: Mirror state plus rendered Ralph prompt.
    """
    mirror_state: CodexGoalMirrorState = read_codex_goal_status(working_directory)
    prompt_request = GoalToRalphHandoffPromptRequest(
        goal_id=mirror_state.goal_id,
        goal_objective_text=mirror_state.objective_text,
        source_paths=source_paths,
        requested_slice=requested_slice,
        constraints=constraints,
        verification_expectations=verification_expectations,
        review_policy=mirror_state.review_policy,
        team_worker_count=mirror_state.team_worker_count,
    )
    prompt: str = build_goal_to_ralph_handoff_prompt(prompt_request)
    result = GoalToRalphHandoffPromptResult(
        mirror_state=mirror_state,
        prompt_request=prompt_request,
        prompt=prompt,
    )
    return result



def advance_tracked_codex_goal(
    *,
    request: CodexGoalAdvanceRequest,
    working_directory: str | None = None,
) -> CodexGoalAdvanceResult:
    mirror_state = read_codex_goal_status(working_directory)
    execution_policy: GoalExecutionPolicy = _apply_native_goal_review_policy(
        execution_policy=request.execution_policy,
        review_policy=mirror_state.review_policy,
    )
    goal_snapshot: CodexGoalSnapshot = build_codex_goal_snapshot(
        goal_id=mirror_state.goal_id,
        objective_text=mirror_state.objective_text,
        capability=request.capability,
        multi_operator_snapshot=request.multi_operator_snapshot,
    )
    decision: GoalDelegationDecision = select_goal_delegation(
        goal_id=mirror_state.goal_id,
        multi_operator_snapshot=request.multi_operator_snapshot,
        execution_policy=execution_policy,
        objective_is_already_structured=request.objective_is_already_structured,
        requires_parallel_fanout=mirror_state.team_worker_count is not None,
        requested_team_worker_count=mirror_state.team_worker_count,
        goal_should_remain_standalone=(
            mirror_state.execution_shape == CodexGoalExecutionShape.GOAL_ONLY
        ),
        goal_objective_text=mirror_state.objective_text,
        ralph_prd_artifact=request.ralph_prd_artifact,
    )
    dispatch_result: GoalDelegationDispatchResult = dispatch_goal_delegation(
        decision=decision,
        multi_operator_snapshot=request.multi_operator_snapshot,
        goal_objective_text=mirror_state.objective_text,
        goal_working_directory=mirror_state.working_directory,
        force_cleanup=request.force_cleanup,
        allow_non_tty=request.allow_non_tty,
    )
    result = CodexGoalAdvanceResult(
        mirror_state=mirror_state,
        goal_snapshot=goal_snapshot,
        execution_policy=execution_policy,
        decision=decision,
        dispatch_result=dispatch_result,
    )
    return result



def select_goal_delegation(
    *,
    goal_id: str,
    multi_operator_snapshot: MultiOperatorSnapshot,
    execution_policy: GoalExecutionPolicy,
    objective_is_already_structured: bool,
    requires_parallel_fanout: bool,
    requested_team_worker_count: int | None = None,
    goal_should_remain_standalone: bool,
    goal_objective_text: str | None = None,
    ralph_prd_artifact: RalphPrdArtifact | None = None,
) -> GoalDelegationDecision:
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
    *,
    decision: GoalDelegationDecision,
    multi_operator_snapshot: MultiOperatorSnapshot,
    goal_objective_text: str,
    goal_working_directory: str | None = None,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> GoalDelegationDispatchResult:
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
