from __future__ import annotations

from pathlib import Path

from omx_remote.execution.invoke import run_omx_command
from omx_remote.runtime.ralph.ralph_control import (
    build_ralph_launch_plan,
    build_ralph_resume_plan,
    build_ralph_team_launch_plan,
    format_preflight_failure as format_ralph_preflight_failure,
    format_resume_outcome as format_ralph_resume_outcome,
)
from omx_remote.runtime.ralph.ralph_state import cleanup_ralph_state
from omx_remote.runtime.ultrawork.ultrawork_control import (
    build_ultrawork_launch_plan,
    build_ultrawork_resume_plan,
    cleanup_ultrawork_state,
    format_preflight_failure as format_ultrawork_preflight_failure,
    format_resume_outcome as format_ultrawork_resume_outcome,
)
from omx_remote.schemas.operator.action_schemas import (
    OperatorActionResult,
    OperatorLane,
    OperatorLoopState,
    OperatorNextAction,
    OperatorRecoveryHint,
)
from omx_remote.schemas.teamwork.operator_schemas import (
    TeamOperatorDispatchInstructionRequest,
    TeamOperatorDispatchOutcome,
    TeamOperatorDispatchTaskRequest,
    TeamOperatorTaskApprovalRequest,
    TeamOperatorWorkerFollowUpOutcome,
    TeamOperatorWorkerRecheckRequest,
)
from omx_remote.shared.omx_enums.teamwork_enums import (
    TeamOperatorDeliveryMode,
    TeamOperatorDispatchOutcomeState,
)
from omx_remote.teamwork.team_operator_facade import (
    dispatch_team_instruction,
    dispatch_team_task,
    request_task_approval,
    request_worker_recheck,
)


def _normalized_message_from_command_result(command_result) -> str:
    """Handles normalized message from command result.
    
    Args:
        command_result [object]: Function argument.
    
    Returns:
        str: Function return value.
    """
    message_source: str
    if command_result.stderr != "":
        message_source = command_result.stderr
    else:
        message_source = command_result.stdout

    normalized_message: str = message_source.strip().lower()
    return normalized_message


def _build_runtime_success_result(
    lane: OperatorLane,
    action: str,
    command_result,
) -> OperatorActionResult:
    """Handles build runtime success result.
    
    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        command_result [object]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    next_action: OperatorNextAction
    summary: str
    recovery_hint: OperatorRecoveryHint | None
    if action == "cleanup":
        next_action = OperatorNextAction.RETRY
        summary = f"{lane} cleanup succeeded and the lane can now be retried."
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.RETRY,
            reason="Cleanup completed, so retrying the lane is now the next safe step.",
            cleanup_first=False,
        )
    else:
        next_action = OperatorNextAction.OBSERVE
        summary = f"{lane} {action} succeeded and the lane can now be observed."
        recovery_hint = None

    result: OperatorActionResult = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=OperatorLoopState.SUCCESS,
        next_action=next_action,
        summary=summary,
        recovery_hint=recovery_hint,
        command_result=command_result,
    )
    return result


def _build_runtime_failure_result(
    lane: OperatorLane,
    action: str,
    command_result,
) -> OperatorActionResult:
    """Handles build runtime failure result.
    
    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        command_result [object]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    normalized_message: str = _normalized_message_from_command_result(command_result)

    if "no resumable" in normalized_message or "no ralph state found" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.LAUNCH,
            reason="No resumable runtime state exists, so a fresh launch is required.",
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.NO_RESUMABLE_STATE_FAILURE,
            next_action=OperatorNextAction.LAUNCH,
            summary=f"{lane} {action} could not resume because no resumable state exists.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "no ultrawork state found" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.LAUNCH,
            reason="No resumable runtime state exists, so a fresh launch is required.",
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.NO_RESUMABLE_STATE_FAILURE,
            next_action=OperatorNextAction.LAUNCH,
            summary=f"{lane} {action} could not resume because no resumable state exists.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "existing resumable" in normalized_message or "cleanup-stale" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.CLEANUP,
            reason="Existing or stale runtime state blocks the lane, so cleanup is required before retrying.",
            cleanup_first=True,
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.STALE_STATE_FAILURE,
            next_action=OperatorNextAction.CLEANUP,
            summary=f"{lane} {action} is blocked by stale or already-resumable state.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "dirty" in normalized_message and "workspace" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.CLEANUP,
            reason="A dirty workspace blocks the lane, so workspace cleanup is required before retrying.",
            cleanup_first=True,
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.DIRTY_WORKSPACE_FAILURE,
            next_action=OperatorNextAction.CLEANUP,
            summary=f"{lane} {action} is blocked by a dirty workspace.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    if "approval" in normalized_message:
        recovery_hint = OperatorRecoveryHint(
            next_action=OperatorNextAction.ESCALATE,
            reason="Approval is required before the lane can continue.",
        )
        result = OperatorActionResult(
            lane=lane,
            action=action,
            loop_state=OperatorLoopState.BLOCKED_APPROVAL_NEEDED,
            next_action=OperatorNextAction.ESCALATE,
            summary=f"{lane} {action} is blocked on approval.",
            recovery_hint=recovery_hint,
            command_result=command_result,
        )
        return result

    recovery_hint = OperatorRecoveryHint(
        next_action=OperatorNextAction.ESCALATE,
        reason="The lane failed without a known recovery pattern, so escalation is the safest next step.",
    )
    result = OperatorActionResult(
        lane=lane,
        action=action,
        loop_state=OperatorLoopState.TERMINAL_FAILURE,
        next_action=OperatorNextAction.ESCALATE,
        summary=f"{lane} {action} failed without a standardized recovery path.",
        recovery_hint=recovery_hint,
        command_result=command_result,
    )
    return result


def _normalize_runtime_command_result(
    lane: OperatorLane,
    action: str,
    command_result,
) -> OperatorActionResult:
    """Handles normalize runtime command result.
    
    Args:
        lane [OperatorLane]: Function argument.
        action [str]: Function argument.
        command_result [object]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    if command_result.exit_code == 0:
        result: OperatorActionResult = _build_runtime_success_result(
            lane=lane,
            action=action,
            command_result=command_result,
        )
        return result

    result = _build_runtime_failure_result(
        lane=lane,
        action=action,
        command_result=command_result,
    )
    return result


def _normalize_team_dispatch_result(
    action: str,
    dispatch_result: TeamOperatorDispatchOutcome,
    unverified_loop_state: OperatorLoopState,
    unverified_next_action: OperatorNextAction,
) -> OperatorActionResult:
    """Handles normalize team dispatch result.
    
    Args:
        action [str]: Function argument.
        dispatch_result [TeamOperatorDispatchOutcome]: Function argument.
        unverified_loop_state [OperatorLoopState]: Function argument.
        unverified_next_action [OperatorNextAction]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    if dispatch_result.outcome == TeamOperatorDispatchOutcomeState.ACCEPTED:
        accepted_result: OperatorActionResult = OperatorActionResult(
            lane=OperatorLane.TEAM,
            action=action,
            loop_state=OperatorLoopState.SUCCESS,
            next_action=OperatorNextAction.OBSERVE,
            summary=f"team {action} completed and the lane can now be observed.",
            recovery_hint=None,
            command_result=dispatch_result.command_result,
        )
        return accepted_result

    if (
        dispatch_result.outcome
        == TeamOperatorDispatchOutcomeState.ACCEPTED_BUT_UNVERIFIED
    ):
        recovery_hint = OperatorRecoveryHint(
            next_action=unverified_next_action,
            reason=dispatch_result.reason,
        )
        unverified_result: OperatorActionResult = OperatorActionResult(
            lane=OperatorLane.TEAM,
            action=action,
            loop_state=unverified_loop_state,
            next_action=unverified_next_action,
            summary=f"team {action} was accepted by OMX but still needs follow-up confirmation.",
            recovery_hint=recovery_hint,
            command_result=dispatch_result.command_result,
        )
        return unverified_result

    recovery_hint = OperatorRecoveryHint(
        next_action=OperatorNextAction.ESCALATE,
        reason=dispatch_result.reason,
    )
    failed_result: OperatorActionResult = OperatorActionResult(
        lane=OperatorLane.TEAM,
        action=action,
        loop_state=OperatorLoopState.TERMINAL_FAILURE,
        next_action=OperatorNextAction.ESCALATE,
        summary=f"team {action} failed and needs escalation.",
        recovery_hint=recovery_hint,
        command_result=dispatch_result.command_result,
    )
    return failed_result



def operate_ralph_launch(
    task: str,
    force_cleanup: bool,
    allow_non_tty: bool,
) -> OperatorActionResult:
    """Run the standardized Ralph launch loop and return one typed operator result.
    
    Args:
        task [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    try:
        command, _warnings = build_ralph_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
        )
    except ValueError as error:
        command_result = format_ralph_preflight_failure(str(error))
        result: OperatorActionResult = _normalize_runtime_command_result(
            lane=OperatorLane.RALPH,
            action="launch",
            command_result=command_result,
        )
        return result

    command_result = run_omx_command(command)
    result = _normalize_runtime_command_result(
        lane=OperatorLane.RALPH,
        action="launch",
        command_result=command_result,
    )
    return result



def operate_ralph_resume() -> OperatorActionResult:
    """Run the standardized Ralph resume loop and return one typed operator result.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    try:
        command, _warnings = build_ralph_resume_plan()
    except ValueError as error:
        command_result = format_ralph_preflight_failure(str(error))
        result: OperatorActionResult = _normalize_runtime_command_result(
            lane=OperatorLane.RALPH,
            action="resume",
            command_result=command_result,
        )
        return result

    raw_command_result = run_omx_command(command)
    command_result = format_ralph_resume_outcome(raw_command_result)
    result = _normalize_runtime_command_result(
        lane=OperatorLane.RALPH,
        action="resume",
        command_result=command_result,
    )
    return result



def operate_ralph_team_launch(allow_non_tty: bool) -> OperatorActionResult:
    """Run the Ralph-owned Team launch loop and return one typed operator result.
    
    Args:
        allow_non_tty [bool]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    try:
        command, _warnings = build_ralph_team_launch_plan(
            allow_non_tty=allow_non_tty,
            require_live_owner_preflight=True,
        )
    except ValueError as error:
        command_result = format_ralph_preflight_failure(str(error))
        result: OperatorActionResult = _normalize_runtime_command_result(
            lane=OperatorLane.TEAM,
            action="launch",
            command_result=command_result,
        )
        return result

    command_result = run_omx_command(command)
    result = _normalize_runtime_command_result(
        lane=OperatorLane.TEAM,
        action="launch",
        command_result=command_result,
    )
    return result



def operate_ralph_cleanup(workspace_root: Path | None = None) -> OperatorActionResult:
    """Run the standardized Ralph cleanup loop and return one typed operator result.
    
    Args:
        workspace_root [Path | None]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    removed_paths: list[str] = cleanup_ralph_state(workspace_root=workspace_root)
    summary: str
    if removed_paths:
        summary = "ralph cleanup removed stale runtime state and the lane can now be retried."
    else:
        summary = "ralph cleanup found no stale runtime files and the lane can now be retried."

    recovery_hint = OperatorRecoveryHint(
        next_action=OperatorNextAction.RETRY,
        reason="Cleanup completed, so retrying the Ralph lane is now the next safe step.",
    )
    result: OperatorActionResult = OperatorActionResult(
        lane=OperatorLane.RALPH,
        action="cleanup",
        loop_state=OperatorLoopState.SUCCESS,
        next_action=OperatorNextAction.RETRY,
        summary=summary,
        recovery_hint=recovery_hint,
        command_result=None,
    )
    return result



def operate_ultrawork_launch(
    task: str,
    force_cleanup: bool,
    allow_non_tty: bool,
    team_size: int,
    team_role: str,
) -> OperatorActionResult:
    """Run the standardized Ultrawork launch loop and return one typed operator result.
    
    Args:
        task [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
        team_size [int]: Function argument.
        team_role [str]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    try:
        command, _warnings = build_ultrawork_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
            team_size=team_size,
            team_role=team_role,
        )
    except ValueError as error:
        command_result = format_ultrawork_preflight_failure(str(error))
        result: OperatorActionResult = _normalize_runtime_command_result(
            lane=OperatorLane.ULTRAWORK,
            action="launch",
            command_result=command_result,
        )
        return result

    command_result = run_omx_command(command)
    result = _normalize_runtime_command_result(
        lane=OperatorLane.ULTRAWORK,
        action="launch",
        command_result=command_result,
    )
    return result



def operate_ultrawork_resume(team_name: str) -> OperatorActionResult:
    """Run the standardized Ultrawork resume loop and return one typed operator result.
    
    Args:
        team_name [str]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    try:
        command, _warnings = build_ultrawork_resume_plan(team_name)
    except ValueError as error:
        command_result = format_ultrawork_preflight_failure(str(error))
        result: OperatorActionResult = _normalize_runtime_command_result(
            lane=OperatorLane.ULTRAWORK,
            action="resume",
            command_result=command_result,
        )
        return result

    raw_command_result = run_omx_command(command)
    command_result = format_ultrawork_resume_outcome(raw_command_result, team_name=team_name)
    result = _normalize_runtime_command_result(
        lane=OperatorLane.ULTRAWORK,
        action="resume",
        command_result=command_result,
    )
    return result



def operate_ultrawork_cleanup(workspace_root: Path | None = None) -> OperatorActionResult:
    """Run the standardized Ultrawork cleanup loop and return one typed operator result.
    
    Args:
        workspace_root [Path | None]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    removed_paths: list[str] = cleanup_ultrawork_state(workspace_root=workspace_root)
    summary: str
    if removed_paths:
        summary = "ultrawork cleanup removed stale runtime state and the lane can now be retried."
    else:
        summary = "ultrawork cleanup found no stale runtime files and the lane can now be retried."

    recovery_hint = OperatorRecoveryHint(
        next_action=OperatorNextAction.RETRY,
        reason="Cleanup completed, so retrying the Ultrawork lane is now the next safe step.",
    )
    result: OperatorActionResult = OperatorActionResult(
        lane=OperatorLane.ULTRAWORK,
        action="cleanup",
        loop_state=OperatorLoopState.SUCCESS,
        next_action=OperatorNextAction.RETRY,
        summary=summary,
        recovery_hint=recovery_hint,
        command_result=None,
    )
    return result


async def operate_team_instruction(
    request: TeamOperatorDispatchInstructionRequest,
) -> OperatorActionResult:
    """Run the standardized team-instruction loop and return one typed operator result.
    
    Args:
        request [TeamOperatorDispatchInstructionRequest]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    dispatch_result: TeamOperatorDispatchOutcome = await dispatch_team_instruction(request)
    result: OperatorActionResult = _normalize_team_dispatch_result(
        action="instruction-dispatch",
        dispatch_result=dispatch_result,
        unverified_loop_state=OperatorLoopState.RESUMABLE_LATER,
        unverified_next_action=OperatorNextAction.OBSERVE,
    )
    return result


async def operate_team_task(
    request: TeamOperatorDispatchTaskRequest,
) -> OperatorActionResult:
    """Run the standardized team-task loop and return one typed operator result.
    
    Args:
        request [TeamOperatorDispatchTaskRequest]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    dispatch_result: TeamOperatorDispatchOutcome = await dispatch_team_task(request)
    result: OperatorActionResult = _normalize_team_dispatch_result(
        action="task-dispatch",
        dispatch_result=dispatch_result,
        unverified_loop_state=OperatorLoopState.RESUMABLE_LATER,
        unverified_next_action=OperatorNextAction.OBSERVE,
    )
    return result


async def operate_team_task_approval(
    request: TeamOperatorTaskApprovalRequest,
) -> OperatorActionResult:
    """Run the standardized team task-approval loop and return one typed operator result.
    
    Args:
        request [TeamOperatorTaskApprovalRequest]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    dispatch_result: TeamOperatorDispatchOutcome = await request_task_approval(request)
    result: OperatorActionResult = _normalize_team_dispatch_result(
        action="task-approval",
        dispatch_result=dispatch_result,
        unverified_loop_state=OperatorLoopState.BLOCKED_APPROVAL_NEEDED,
        unverified_next_action=OperatorNextAction.OBSERVE,
    )
    return result


async def operate_team_worker_recheck(
    request: TeamOperatorWorkerRecheckRequest,
) -> OperatorActionResult:
    """Run the standardized team worker-recheck loop and return one typed operator result.
    
    Args:
        request [TeamOperatorWorkerRecheckRequest]: Function argument.
    
    Returns:
        OperatorActionResult: Function return value.
    """
    follow_up_result: TeamOperatorWorkerFollowUpOutcome = await request_worker_recheck(request)
    dispatch_result: TeamOperatorDispatchOutcome = follow_up_result.dispatch_result
    next_action: OperatorNextAction
    if follow_up_result.selected_delivery_mode == TeamOperatorDeliveryMode.DURABLE_INBOX:
        next_action = OperatorNextAction.RESUME
    else:
        next_action = OperatorNextAction.OBSERVE

    result: OperatorActionResult = _normalize_team_dispatch_result(
        action="worker-recheck",
        dispatch_result=dispatch_result,
        unverified_loop_state=OperatorLoopState.RESUMABLE_LATER,
        unverified_next_action=next_action,
    )
    return result
