from omx_remote.adapter_types.type_contract.operator_contract_type import (
    BLOCKING_LOOP_STATES,
)
from omx_remote.runtime.goal.codex_goal_runtime import (
    read_codex_goal_status,
)
from omx_remote.runtime.goal.goal_delegation import (
    _apply_native_goal_review_policy,
    dispatch_goal_delegation,
    select_goal_delegation,
)
from omx_remote.runtime.goal.goal_lifecycle_decision import (
    build_goal_lifecycle_decision,
)
from omx_remote.runtime.goal.ralph_handoff_prompt import (
    GoalToRalphHandoffPromptRenderer,
    build_goal_to_ralph_handoff_prompt,
)
from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalExecutionShape,
    CodexGoalMirrorState,
)
from omx_remote.schemas.codex_goal.supervisor_schemas import (
    CodexGoalAdvanceRequest,
    CodexGoalAdvanceResult,
    CodexGoalCapabilitySnapshot,
    CodexGoalSnapshot,
    CodexGoalSource,
    CodexGoalStatus,
    GoalDelegationDecision,
    GoalDelegationDispatchResult,
    GoalExecutionPolicy,
    GoalToRalphHandoffPromptRequest,
    GoalToRalphHandoffPromptResult,
)
from omx_remote.schemas.multi_operator.snapshot_schemas import (
    ManagedOmxFlow,
    MultiOperatorSnapshot,
)
from omx_remote.schemas.operator.action_schemas import OperatorActionResult

__all__ = (
    "GoalToRalphHandoffPromptRenderer",
    "advance_tracked_codex_goal",
    "build_codex_goal_snapshot",
    "build_goal_lifecycle_decision",
    "build_goal_to_ralph_handoff_prompt",
    "dispatch_goal_delegation",
    "prepare_tracked_codex_goal_ralph_handoff_prompt",
    "select_goal_delegation",
)


def _build_open_blockers(multi_operator_snapshot: MultiOperatorSnapshot) -> list[str]:
    """Handles build open blockers.
    
    Args:
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
    
    Returns:
        list[str]: Function return value.
    """
    open_blockers: list[str] = []

    flow: ManagedOmxFlow
    for flow in multi_operator_snapshot.flows.root:
        flow_result: OperatorActionResult | None = flow.last_result
        if flow_result is None:
            continue

        if flow_result.loop_state not in BLOCKING_LOOP_STATES:
            continue

        blocker_text = f"{flow.flow_id}: {flow_result.summary}"
        open_blockers.append(blocker_text)

    return open_blockers



def build_codex_goal_snapshot(
    goal_id: str,
    objective_text: str,
    capability: CodexGoalCapabilitySnapshot,
    multi_operator_snapshot: MultiOperatorSnapshot,
) -> CodexGoalSnapshot:
    """Handles build codex goal snapshot.
    
    Args:
        goal_id [str]: Function argument.
        objective_text [str]: Function argument.
        capability [CodexGoalCapabilitySnapshot]: Function argument.
        multi_operator_snapshot [MultiOperatorSnapshot]: Function argument.
    
    Returns:
        CodexGoalSnapshot: Function return value.
    """
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




def prepare_tracked_codex_goal_ralph_handoff_prompt(
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
    request: CodexGoalAdvanceRequest,
    working_directory: str | None = None,
) -> CodexGoalAdvanceResult:
    """Handles advance tracked codex goal.
    
    Args:
        request [CodexGoalAdvanceRequest]: Function argument.
        working_directory [str | None]: Function argument.
    
    Returns:
        CodexGoalAdvanceResult: Function return value.
    """
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



