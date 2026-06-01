from omx_remote.schemas.invoke_command_schemas import OmxCommandResult
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiBroadcastRequest,
    TeamApiCreateTaskRequest,
    TeamApiReadWorkerStatusRequest,
    TeamApiSendMessageRequest,
    TeamApiWorkerInboxWriteRequest,
    TeamApiWriteTaskApprovalRequest,
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
    TeamOperatorDispatchOperation,
    TeamOperatorDispatchOutcomeState,
)
from omx_remote.teamwork.team_api_control import (
    broadcast_team_message,
    create_team_task,
    send_team_message,
    write_team_task_approval,
    write_team_worker_inbox,
)
from omx_remote.teamwork.team_api_snapshot import read_team_api_read_worker_status


def _build_dispatch_outcome(
    selected_operation: TeamOperatorDispatchOperation,
    exit_code: int,
    success_reason: str,
    unverified_reason: str | None,
    command_result: OmxCommandResult,
) -> TeamOperatorDispatchOutcome:
    """Builds one Hermes-oriented operator outcome from one low-level command result.

    Args:
        selected_operation [str]: Low-level OMX operation chosen by the facade.
        exit_code [int]: Command exit code returned from OMX.
        success_reason [str]: Reason text for a clean accepted outcome.
        unverified_reason [str | None]: Reason text for a success-like but unverified outcome.
        command_result [object]: Shared low-level OMX command-result payload.

    Returns:
        TeamOperatorDispatchOutcome: Typed facade outcome that exposes the chosen operation and follow-up need.
    """
    if exit_code != 0:
        failed_outcome: TeamOperatorDispatchOutcome = TeamOperatorDispatchOutcome(
            selected_operation=selected_operation,
            outcome=TeamOperatorDispatchOutcomeState.FAILED,
            needs_follow_up=True,
            reason="OMX command returned a non-zero exit code.",
            command_result=command_result,
        )
        return failed_outcome

    if unverified_reason is not None:
        unverified_outcome: TeamOperatorDispatchOutcome = TeamOperatorDispatchOutcome(
            selected_operation=selected_operation,
            outcome=TeamOperatorDispatchOutcomeState.ACCEPTED_BUT_UNVERIFIED,
            needs_follow_up=True,
            reason=unverified_reason,
            command_result=command_result,
        )
        return unverified_outcome

    accepted_outcome: TeamOperatorDispatchOutcome = TeamOperatorDispatchOutcome(
        selected_operation=selected_operation,
        outcome=TeamOperatorDispatchOutcomeState.ACCEPTED,
        needs_follow_up=False,
        reason=success_reason,
        command_result=command_result,
    )
    return accepted_outcome


async def dispatch_team_instruction(
    request: TeamOperatorDispatchInstructionRequest,
) -> TeamOperatorDispatchOutcome:
    """Dispatches one Hermes-oriented team instruction through the most suitable low-level OMX write.

    Args:
        request [TeamOperatorDispatchInstructionRequest]: High-level instruction request that decides between direct message, durable inbox write, or broadcast.

    Returns:
        TeamOperatorDispatchOutcome: Facade outcome describing the selected operation and whether follow-up is needed.
    """
    if request.to_worker is None:
        command_result = await broadcast_team_message(
            TeamApiBroadcastRequest(
                team_name=request.team_name,
                from_worker=request.from_worker,
                body=request.body,
            )
        )
        result: TeamOperatorDispatchOutcome = _build_dispatch_outcome(
            selected_operation=TeamOperatorDispatchOperation.BROADCAST,
            exit_code=command_result.exit_code,
            success_reason="Broadcast accepted by OMX.",
            unverified_reason=None,
            command_result=command_result,
        )
        return result

    if request.durable_delivery:
        command_result = await write_team_worker_inbox(
            TeamApiWorkerInboxWriteRequest(
                team_name=request.team_name,
                worker=request.to_worker,
                content=request.body,
            )
        )
        result = _build_dispatch_outcome(
            selected_operation=TeamOperatorDispatchOperation.WRITE_WORKER_INBOX,
            exit_code=command_result.exit_code,
            success_reason="Worker inbox update accepted by OMX.",
            unverified_reason=(
                "write-worker-inbox can report success without proving mailbox state, so follow-up read is still recommended."
            ),
            command_result=command_result,
        )
        return result

    command_result = await send_team_message(
        TeamApiSendMessageRequest(
            team_name=request.team_name,
            from_worker=request.from_worker,
            to_worker=request.to_worker,
            body=request.body,
        )
    )
    result = _build_dispatch_outcome(
        selected_operation=TeamOperatorDispatchOperation.SEND_MESSAGE,
        exit_code=command_result.exit_code,
        success_reason="Direct message accepted by OMX.",
        unverified_reason=None,
        command_result=command_result,
    )
    return result


async def dispatch_team_task(
    request: TeamOperatorDispatchTaskRequest,
) -> TeamOperatorDispatchOutcome:
    """Dispatches one Hermes-oriented team task creation request.

    Args:
        request [TeamOperatorDispatchTaskRequest]: High-level task request that owns subject, description, and optional assignment metadata.

    Returns:
        TeamOperatorDispatchOutcome: Facade outcome describing the create-task attempt and follow-up need.
    """
    command_result = await create_team_task(
        TeamApiCreateTaskRequest(
            team_name=request.team_name,
            subject=request.subject,
            description=request.description,
            owner=request.owner,
            blocked_by=request.blocked_by,
            requires_code_change=request.requires_code_change,
        )
    )
    result: TeamOperatorDispatchOutcome = _build_dispatch_outcome(
        selected_operation=TeamOperatorDispatchOperation.CREATE_TASK,
        exit_code=command_result.exit_code,
        success_reason="Task creation accepted by OMX.",
        unverified_reason=(
            "Task creation completed without a typed task-id promotion here, so follow-up task inspection is still recommended."
        ),
        command_result=command_result,
    )
    return result


async def request_task_approval(
    request: TeamOperatorTaskApprovalRequest,
) -> TeamOperatorDispatchOutcome:
    """Dispatches one Hermes-oriented task approval request.

    Args:
        request [TeamOperatorTaskApprovalRequest]: High-level task-approval request that packages review status and decision text.

    Returns:
        TeamOperatorDispatchOutcome: Facade outcome describing the approval-write attempt and follow-up need.
    """
    command_result = await write_team_task_approval(
        TeamApiWriteTaskApprovalRequest(
            team_name=request.team_name,
            task_id=request.task_id,
            status=request.status,
            reviewer=request.reviewer,
            decision_reason=request.decision_reason,
            required=request.required,
        )
    )
    result: TeamOperatorDispatchOutcome = _build_dispatch_outcome(
        selected_operation=TeamOperatorDispatchOperation.WRITE_TASK_APPROVAL,
        exit_code=command_result.exit_code,
        success_reason="Task approval write accepted by OMX.",
        unverified_reason=(
            "write-task-approval can return success-like payloads without proving approval state, so follow-up inspection is still recommended."
        ),
        command_result=command_result,
    )
    return result


async def request_worker_recheck(
    request: TeamOperatorWorkerRecheckRequest,
) -> TeamOperatorWorkerFollowUpOutcome:
    """Chooses the next Hermes worker follow-up delivery mode from typed worker state.

    Args:
        request [TeamOperatorWorkerRecheckRequest]: High-level follow-up request that inspects worker state before selecting direct or durable delivery.

    Returns:
        TeamOperatorWorkerFollowUpOutcome: Facade outcome that exposes worker state, selected delivery mode, and nested dispatch result.
    """
    worker_status = await read_team_api_read_worker_status(
        TeamApiReadWorkerStatusRequest(
            team_name=request.team_name,
            worker=request.worker,
        )
    )

    durable_delivery: bool = worker_status.state == "unknown"
    selected_delivery_mode: TeamOperatorDeliveryMode
    if durable_delivery:
        selected_delivery_mode = TeamOperatorDeliveryMode.DURABLE_INBOX
    else:
        selected_delivery_mode = TeamOperatorDeliveryMode.DIRECT_MESSAGE

    dispatch_result = await dispatch_team_instruction(
        TeamOperatorDispatchInstructionRequest(
            team_name=request.team_name,
            from_worker=request.from_worker,
            to_worker=request.worker,
            body=request.body,
            durable_delivery=durable_delivery,
        )
    )

    result: TeamOperatorWorkerFollowUpOutcome = TeamOperatorWorkerFollowUpOutcome(
        worker_state=worker_status.state,
        selected_delivery_mode=selected_delivery_mode,
        dispatch_result=dispatch_result,
    )
    return result
