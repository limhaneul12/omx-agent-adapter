"""Async wrappers for mutating OMX Team API control commands."""

import msgspec
import orjson

from omx_remote.adapter_types.teams_type.team_api_control_payloads import (
    TeamApiBroadcastPayload,
    TeamApiClaimTaskPayload,
    TeamApiCleanupPayload,
    TeamApiControlPayload,
    TeamApiCreateTaskPayload,
    TeamApiMailboxMarkDeliveredPayload,
    TeamApiMailboxMarkNotifiedPayload,
    TeamApiOptionalBool,
    TeamApiOptionalInt,
    TeamApiOptionalString,
    TeamApiOptionalStringItems,
    TeamApiOrphanCleanupPayload,
    TeamApiReadShutdownAckPayload,
    TeamApiReadTaskApprovalPayload,
    TeamApiReadTaskPayload,
    TeamApiReleaseTaskClaimPayload,
    TeamApiSendMessagePayload,
    TeamApiStringItems,
    TeamApiTransitionTaskStatusPayload,
    TeamApiUpdateTaskPayload,
    TeamApiWorkerInboxWritePayload,
    TeamApiWriteShutdownPayload,
    TeamApiWriteTaskApprovalPayload,
)
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.invoke_command_schemas import OmxCommandResult
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiBroadcastRequest,
    TeamApiClaimTaskRequest,
    TeamApiCleanupRequest,
    TeamApiCreateTaskRequest,
    TeamApiMailboxMarkDeliveredRequest,
    TeamApiMailboxMarkNotifiedRequest,
    TeamApiOrphanCleanupRequest,
    TeamApiReadShutdownAckRequest,
    TeamApiReadTaskApprovalRequest,
    TeamApiReadTaskRequest,
    TeamApiReleaseTaskClaimRequest,
    TeamApiSendMessageRequest,
    TeamApiTransitionTaskStatusRequest,
    TeamApiUpdateTaskRequest,
    TeamApiWorkerInboxWriteRequest,
    TeamApiWriteShutdownRequest,
    TeamApiWriteTaskApprovalRequest,
)


def _optional_string(value: str | None) -> TeamApiOptionalString:
    """Convert an optional request string to an omitted msgspec field value.

    Args:
        value [str | None]: Optional request value.

    Returns:
        TeamApiOptionalString: Original string or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalString = msgspec.UNSET if value is None else value
    return result


def _optional_bool(value: bool | None) -> TeamApiOptionalBool:
    """Convert an optional request bool to an omitted msgspec field value.

    Args:
        value [bool | None]: Optional request value.

    Returns:
        TeamApiOptionalBool: Original bool or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalBool = msgspec.UNSET if value is None else value
    return result


def _optional_int(value: int | None) -> TeamApiOptionalInt:
    """Convert an optional request int to an omitted msgspec field value.

    Args:
        value [int | None]: Optional request value.

    Returns:
        TeamApiOptionalInt: Original int or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalInt = msgspec.UNSET if value is None else value
    return result


def _optional_string_items(
    values: TeamApiStringItems | None,
) -> TeamApiOptionalStringItems:
    """Convert optional string items to an omitted msgspec field value.

    Args:
        values [TeamApiStringItems | None]: Optional request tuple.

    Returns:
        TeamApiOptionalStringItems: Original tuple or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalStringItems = msgspec.UNSET if values is None else values
    return result


def _nonempty_string_items(values: TeamApiStringItems) -> TeamApiOptionalStringItems:
    """Convert an empty tuple into an omitted msgspec field value.

    Args:
        values [TeamApiStringItems]: Required request tuple where emptiness means omission.

    Returns:
        TeamApiOptionalStringItems: Non-empty tuple or `msgspec.UNSET` when empty.
    """
    result: TeamApiOptionalStringItems = values if values else msgspec.UNSET
    return result


async def _run_team_api_command(
    action: str,
    payload: TeamApiControlPayload,
) -> OmxCommandResult:
    """Run one Team API OMX command.

    Args:
        action [str]: Team API action name.
        payload [TeamApiControlPayload]: Typed JSON payload for the action.

    Returns:
        OmxCommandResult: Completed OMX command result.
    """
    payload_json = orjson.dumps(msgspec.to_builtins(payload)).decode()
    command_arguments: tuple[str, ...] = (
        "team",
        "api",
        action,
        "--input",
        payload_json,
        "--json",
    )
    result: OmxCommandResult = await run_blocking_call(
        run_omx_command,
        arguments=command_arguments,
    )
    return result


async def send_team_message(request: TeamApiSendMessageRequest) -> OmxCommandResult:
    """Send one direct team message through `omx team api send-message`.

    Args:
        request [TeamApiSendMessageRequest]: Typed request boundary for message delivery.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed send-message call.
    """
    result = await _run_team_api_command(
        action="send-message",
        payload=TeamApiSendMessagePayload(
            team_name=request.team_name,
            from_worker=request.from_worker,
            to_worker=request.to_worker,
            body=request.body,
        ),
    )
    return result


async def write_team_worker_inbox(
    request: TeamApiWorkerInboxWriteRequest,
) -> OmxCommandResult:
    """Write one worker inbox entry through `omx team api write-worker-inbox`.

    Args:
        request [TeamApiWorkerInboxWriteRequest]: Typed request boundary for worker inbox writes.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed write-worker-inbox call.
    """
    result = await _run_team_api_command(
        action="write-worker-inbox",
        payload=TeamApiWorkerInboxWritePayload(
            team_name=request.team_name,
            worker=request.worker,
            content=request.content,
        ),
    )
    return result


async def broadcast_team_message(request: TeamApiBroadcastRequest) -> OmxCommandResult:
    """Broadcast one team message through `omx team api broadcast`.

    Args:
        request [TeamApiBroadcastRequest]: Typed request boundary for team-wide broadcast delivery.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed broadcast call.
    """
    result = await _run_team_api_command(
        action="broadcast",
        payload=TeamApiBroadcastPayload(
            team_name=request.team_name,
            from_worker=request.from_worker,
            body=request.body,
        ),
    )
    return result


async def create_team_task(request: TeamApiCreateTaskRequest) -> OmxCommandResult:
    """Create one team task through `omx team api create-task`.

    Args:
        request [TeamApiCreateTaskRequest]: Typed request boundary for team task creation.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed create-task call.
    """
    task_payload = TeamApiCreateTaskPayload(
        team_name=request.team_name,
        subject=request.subject,
        description=request.description,
        owner=_optional_string(value=request.owner),
        blocked_by=_nonempty_string_items(values=request.blocked_by),
        requires_code_change=_optional_bool(value=request.requires_code_change),
    )
    result = await _run_team_api_command(action="create-task", payload=task_payload)
    return result


async def read_team_task(request: TeamApiReadTaskRequest) -> OmxCommandResult:
    """Read one team task through `omx team api read-task`.

    Args:
        request [TeamApiReadTaskRequest]: Typed request boundary for reading one team task.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed read-task call.
    """
    result = await _run_team_api_command(
        action="read-task",
        payload=TeamApiReadTaskPayload(
            team_name=request.team_name,
            task_id=request.task_id,
        ),
    )
    return result


async def transition_team_task_status(
    request: TeamApiTransitionTaskStatusRequest,
) -> OmxCommandResult:
    """Transition one team task status through `omx team api transition-task-status`.

    Args:
        request [TeamApiTransitionTaskStatusRequest]: Typed request boundary for one team task-status transition.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed transition-task-status call.
    """
    transition_payload = TeamApiTransitionTaskStatusPayload(
        team_name=request.team_name,
        task_id=request.task_id,
        from_status=request.from_status,
        to_status=request.to_status,
        claim_token=request.claim_token,
        result=_optional_string(value=request.result),
        error=_optional_string(value=request.error),
    )
    result = await _run_team_api_command(
        action="transition-task-status",
        payload=transition_payload,
    )
    return result


async def update_team_task(request: TeamApiUpdateTaskRequest) -> OmxCommandResult:
    """Update one team task metadata record through `omx team api update-task`.

    Args:
        request [TeamApiUpdateTaskRequest]: Typed request boundary for one team task metadata update.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed update-task call.
    """
    update_payload = TeamApiUpdateTaskPayload(
        team_name=request.team_name,
        task_id=request.task_id,
        subject=_optional_string(value=request.subject),
        description=_optional_string(value=request.description),
        blocked_by=_optional_string_items(values=request.blocked_by),
        requires_code_change=_optional_bool(value=request.requires_code_change),
    )
    result = await _run_team_api_command(action="update-task", payload=update_payload)
    return result


async def claim_team_task(request: TeamApiClaimTaskRequest) -> OmxCommandResult:
    """Claim one team task through `omx team api claim-task`.

    Args:
        request [TeamApiClaimTaskRequest]: Typed request boundary for one team task claim.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed claim-task call.
    """
    claim_payload = TeamApiClaimTaskPayload(
        team_name=request.team_name,
        task_id=request.task_id,
        worker=request.worker,
        expected_version=_optional_int(value=request.expected_version),
    )
    result = await _run_team_api_command(action="claim-task", payload=claim_payload)
    return result


async def release_team_task_claim(
    request: TeamApiReleaseTaskClaimRequest,
) -> OmxCommandResult:
    """Release one team task claim through `omx team api release-task-claim`.

    Args:
        request [TeamApiReleaseTaskClaimRequest]: Typed request boundary for one team task-claim release.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed release-task-claim call.
    """
    result = await _run_team_api_command(
        action="release-task-claim",
        payload=TeamApiReleaseTaskClaimPayload(
            team_name=request.team_name,
            task_id=request.task_id,
            claim_token=request.claim_token,
            worker=request.worker,
        ),
    )
    return result


async def read_team_task_approval(
    request: TeamApiReadTaskApprovalRequest,
) -> OmxCommandResult:
    """Read one team task approval record through `omx team api read-task-approval`.

    Args:
        request [TeamApiReadTaskApprovalRequest]: Typed request boundary for one team task-approval read.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed read-task-approval call.
    """
    result = await _run_team_api_command(
        action="read-task-approval",
        payload=TeamApiReadTaskApprovalPayload(
            team_name=request.team_name,
            task_id=request.task_id,
        ),
    )
    return result


async def write_team_task_approval(
    request: TeamApiWriteTaskApprovalRequest,
) -> OmxCommandResult:
    """Write one team task approval record through `omx team api write-task-approval`.

    Args:
        request [TeamApiWriteTaskApprovalRequest]: Typed request boundary for one team task-approval write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed write-task-approval call.
    """
    approval_payload = TeamApiWriteTaskApprovalPayload(
        team_name=request.team_name,
        task_id=request.task_id,
        status=request.status,
        reviewer=request.reviewer,
        decision_reason=request.decision_reason,
        required=_optional_bool(value=request.required),
    )
    result = await _run_team_api_command(
        action="write-task-approval",
        payload=approval_payload,
    )
    return result


async def mark_team_mailbox_delivered(
    request: TeamApiMailboxMarkDeliveredRequest,
) -> OmxCommandResult:
    """Mark one team mailbox message as delivered through `omx team api mailbox-mark-delivered`.

    Args:
        request [TeamApiMailboxMarkDeliveredRequest]: Typed request boundary for one mailbox delivery marker write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed mailbox-mark-delivered call.
    """
    result = await _run_team_api_command(
        action="mailbox-mark-delivered",
        payload=TeamApiMailboxMarkDeliveredPayload(
            team_name=request.team_name,
            worker=request.worker,
            message_id=request.message_id,
        ),
    )
    return result


async def mark_team_mailbox_notified(
    request: TeamApiMailboxMarkNotifiedRequest,
) -> OmxCommandResult:
    """Mark one team mailbox message as notified through `omx team api mailbox-mark-notified`.

    Args:
        request [TeamApiMailboxMarkNotifiedRequest]: Typed request boundary for one mailbox notification marker write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed mailbox-mark-notified call.
    """
    result = await _run_team_api_command(
        action="mailbox-mark-notified",
        payload=TeamApiMailboxMarkNotifiedPayload(
            team_name=request.team_name,
            worker=request.worker,
            message_id=request.message_id,
        ),
    )
    return result


async def write_team_shutdown_request(
    request: TeamApiWriteShutdownRequest,
) -> OmxCommandResult:
    """Write one team shutdown request through `omx team api write-shutdown-request`.

    Args:
        request [TeamApiWriteShutdownRequest]: Typed request boundary for one team shutdown-request write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed write-shutdown-request call.
    """
    result = await _run_team_api_command(
        action="write-shutdown-request",
        payload=TeamApiWriteShutdownPayload(
            team_name=request.team_name,
            worker=request.worker,
            requested_by=request.requested_by,
        ),
    )
    return result


async def read_team_shutdown_ack(
    request: TeamApiReadShutdownAckRequest,
) -> OmxCommandResult:
    """Read one team shutdown ack through `omx team api read-shutdown-ack`.

    Args:
        request [TeamApiReadShutdownAckRequest]: Typed request boundary for one team shutdown-ack read.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed read-shutdown-ack call.
    """
    shutdown_ack_payload = TeamApiReadShutdownAckPayload(
        team_name=request.team_name,
        worker=request.worker,
        min_updated_at=_optional_string(value=request.min_updated_at),
    )
    result = await _run_team_api_command(
        action="read-shutdown-ack",
        payload=shutdown_ack_payload,
    )
    return result


async def cleanup_team_state(request: TeamApiCleanupRequest) -> OmxCommandResult:
    """Run team cleanup through `omx team api cleanup`.

    Args:
        request [TeamApiCleanupRequest]: Typed request boundary for one team cleanup call.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed cleanup call.
    """
    cleanup_payload = TeamApiCleanupPayload(
        team_name=request.team_name,
        force=_optional_bool(value=request.force),
        confirm_issues=_optional_bool(value=request.confirm_issues),
    )
    result = await _run_team_api_command(action="cleanup", payload=cleanup_payload)
    return result


async def cleanup_team_orphans(
    request: TeamApiOrphanCleanupRequest,
) -> OmxCommandResult:
    """Run orphan cleanup through `omx team api orphan-cleanup`.

    Args:
        request [TeamApiOrphanCleanupRequest]: Typed request boundary for one team orphan-cleanup call.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed orphan-cleanup call.
    """
    result = await _run_team_api_command(
        action="orphan-cleanup",
        payload=TeamApiOrphanCleanupPayload(team_name=request.team_name),
    )
    return result
