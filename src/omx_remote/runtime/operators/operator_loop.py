from pathlib import Path

from omx_remote.execution.invoke import run_omx_command
from omx_remote.runtime.operators.operator_result_normalization import (
    normalize_runtime_command_result,
    normalize_team_dispatch_result,
)
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
from omx_remote.schemas.operator_action_schemas import (
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
from omx_remote.shared.omx_enums.teamwork_enums import TeamOperatorDeliveryMode
from omx_remote.teamwork.team_operator_facade import (
    dispatch_team_instruction,
    dispatch_team_task,
    request_task_approval,
    request_worker_recheck,
)


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
        result: OperatorActionResult = normalize_runtime_command_result(
            lane=OperatorLane.RALPH,
            action="launch",
            command_result=command_result,
        )
        return result

    command_result = run_omx_command(command)
    result = normalize_runtime_command_result(
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
        result: OperatorActionResult = normalize_runtime_command_result(
            lane=OperatorLane.RALPH,
            action="resume",
            command_result=command_result,
        )
        return result

    raw_command_result = run_omx_command(command)
    command_result = format_ralph_resume_outcome(raw_command_result)
    result = normalize_runtime_command_result(
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
        result: OperatorActionResult = normalize_runtime_command_result(
            lane=OperatorLane.TEAM,
            action="launch",
            command_result=command_result,
        )
        return result

    command_result = run_omx_command(command)
    result = normalize_runtime_command_result(
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
        summary = (
            "ralph cleanup removed stale runtime state and the lane can now be retried."
        )
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
        result: OperatorActionResult = normalize_runtime_command_result(
            lane=OperatorLane.ULTRAWORK,
            action="launch",
            command_result=command_result,
        )
        return result

    command_result = run_omx_command(command)
    result = normalize_runtime_command_result(
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
        result: OperatorActionResult = normalize_runtime_command_result(
            lane=OperatorLane.ULTRAWORK,
            action="resume",
            command_result=command_result,
        )
        return result

    raw_command_result = run_omx_command(command)
    command_result = format_ultrawork_resume_outcome(
        raw_command_result, team_name=team_name
    )
    result = normalize_runtime_command_result(
        lane=OperatorLane.ULTRAWORK,
        action="resume",
        command_result=command_result,
    )
    return result


def operate_ultrawork_cleanup(
    workspace_root: Path | None = None,
) -> OperatorActionResult:
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
    dispatch_result: TeamOperatorDispatchOutcome = await dispatch_team_instruction(
        request
    )
    result: OperatorActionResult = normalize_team_dispatch_result(
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
    result: OperatorActionResult = normalize_team_dispatch_result(
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
    result: OperatorActionResult = normalize_team_dispatch_result(
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
    follow_up_result: TeamOperatorWorkerFollowUpOutcome = await request_worker_recheck(
        request
    )
    dispatch_result: TeamOperatorDispatchOutcome = follow_up_result.dispatch_result
    next_action: OperatorNextAction
    if (
        follow_up_result.selected_delivery_mode
        == TeamOperatorDeliveryMode.DURABLE_INBOX
    ):
        next_action = OperatorNextAction.RESUME
    else:
        next_action = OperatorNextAction.OBSERVE

    result: OperatorActionResult = normalize_team_dispatch_result(
        action="worker-recheck",
        dispatch_result=dispatch_result,
        unverified_loop_state=OperatorLoopState.RESUMABLE_LATER,
        unverified_next_action=next_action,
    )
    return result
