import asyncio

import orjson

from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.invoke_schemas import OmxCommandResult
from omx_remote.schemas.teamwork_schemas import (
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


async def send_team_message(request: TeamApiSendMessageRequest) -> OmxCommandResult:
    """Sends one direct team message through `omx team api send-message`.

    Args:
        request [TeamApiSendMessageRequest]: Typed request boundary for message delivery.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed send-message call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "send-message",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "from_worker": request.from_worker,
                "to_worker": request.to_worker,
                "body": request.body,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def write_team_worker_inbox(
    request: TeamApiWorkerInboxWriteRequest,
) -> OmxCommandResult:
    """Writes one worker inbox entry through `omx team api write-worker-inbox`.

    Args:
        request [TeamApiWorkerInboxWriteRequest]: Typed request boundary for worker inbox writes.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed write-worker-inbox call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "write-worker-inbox",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "worker": request.worker,
                "content": request.content,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def broadcast_team_message(request: TeamApiBroadcastRequest) -> OmxCommandResult:
    """Broadcasts one team message through `omx team api broadcast`.

    Args:
        request [TeamApiBroadcastRequest]: Typed request boundary for team-wide broadcast delivery.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed broadcast call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "broadcast",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "from_worker": request.from_worker,
                "body": request.body,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def create_team_task(request: TeamApiCreateTaskRequest) -> OmxCommandResult:
    """Creates one team task through `omx team api create-task`.

    Args:
        request [TeamApiCreateTaskRequest]: Typed request boundary for team task creation.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed create-task call.
    """
    task_payload: dict[str, object] = {
        "team_name": request.team_name,
        "subject": request.subject,
        "description": request.description,
    }
    if request.owner is not None:
        task_payload["owner"] = request.owner
    if request.blocked_by:
        task_payload["blocked_by"] = request.blocked_by
    if request.requires_code_change is not None:
        task_payload["requires_code_change"] = request.requires_code_change

    command_arguments: list[str] = [
        "team",
        "api",
        "create-task",
        "--input",
        orjson.dumps(task_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def read_team_task(request: TeamApiReadTaskRequest) -> OmxCommandResult:
    """Reads one team task through `omx team api read-task`.

    Args:
        request [TeamApiReadTaskRequest]: Typed request boundary for reading one team task.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed read-task call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "read-task",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "task_id": request.task_id,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def transition_team_task_status(
    request: TeamApiTransitionTaskStatusRequest,
) -> OmxCommandResult:
    """Transitions one team task status through `omx team api transition-task-status`.

    Args:
        request [TeamApiTransitionTaskStatusRequest]: Typed request boundary for one team task-status transition.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed transition-task-status call.
    """
    transition_payload: dict[str, object] = {
        "team_name": request.team_name,
        "task_id": request.task_id,
        "from": request.from_status,
        "to": request.to_status,
        "claim_token": request.claim_token,
    }
    if request.result is not None:
        transition_payload["result"] = request.result
    if request.error is not None:
        transition_payload["error"] = request.error

    command_arguments: list[str] = [
        "team",
        "api",
        "transition-task-status",
        "--input",
        orjson.dumps(transition_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def update_team_task(request: TeamApiUpdateTaskRequest) -> OmxCommandResult:
    """Updates one team task metadata record through `omx team api update-task`.

    Args:
        request [TeamApiUpdateTaskRequest]: Typed request boundary for one team task metadata update.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed update-task call.
    """
    update_payload: dict[str, object] = {
        "team_name": request.team_name,
        "task_id": request.task_id,
    }
    if request.subject is not None:
        update_payload["subject"] = request.subject
    if request.description is not None:
        update_payload["description"] = request.description
    if request.blocked_by is not None:
        update_payload["blocked_by"] = request.blocked_by
    if request.requires_code_change is not None:
        update_payload["requires_code_change"] = request.requires_code_change

    command_arguments: list[str] = [
        "team",
        "api",
        "update-task",
        "--input",
        orjson.dumps(update_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def claim_team_task(request: TeamApiClaimTaskRequest) -> OmxCommandResult:
    """Claims one team task through `omx team api claim-task`.

    Args:
        request [TeamApiClaimTaskRequest]: Typed request boundary for one team task claim.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed claim-task call.
    """
    claim_payload: dict[str, object] = {
        "team_name": request.team_name,
        "task_id": request.task_id,
        "worker": request.worker,
    }
    if request.expected_version is not None:
        claim_payload["expected_version"] = request.expected_version

    command_arguments: list[str] = [
        "team",
        "api",
        "claim-task",
        "--input",
        orjson.dumps(claim_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def release_team_task_claim(
    request: TeamApiReleaseTaskClaimRequest,
) -> OmxCommandResult:
    """Releases one team task claim through `omx team api release-task-claim`.

    Args:
        request [TeamApiReleaseTaskClaimRequest]: Typed request boundary for one team task-claim release.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed release-task-claim call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "release-task-claim",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "task_id": request.task_id,
                "claim_token": request.claim_token,
                "worker": request.worker,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def read_team_task_approval(
    request: TeamApiReadTaskApprovalRequest,
) -> OmxCommandResult:
    """Reads one team task approval record through `omx team api read-task-approval`.

    Args:
        request [TeamApiReadTaskApprovalRequest]: Typed request boundary for one team task-approval read.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed read-task-approval call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "read-task-approval",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "task_id": request.task_id,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def write_team_task_approval(
    request: TeamApiWriteTaskApprovalRequest,
) -> OmxCommandResult:
    """Writes one team task approval record through `omx team api write-task-approval`.

    Args:
        request [TeamApiWriteTaskApprovalRequest]: Typed request boundary for one team task-approval write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed write-task-approval call.
    """
    approval_payload: dict[str, object] = {
        "team_name": request.team_name,
        "task_id": request.task_id,
        "status": request.status,
        "reviewer": request.reviewer,
        "decision_reason": request.decision_reason,
    }
    if request.required is not None:
        approval_payload["required"] = request.required

    command_arguments: list[str] = [
        "team",
        "api",
        "write-task-approval",
        "--input",
        orjson.dumps(approval_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def mark_team_mailbox_delivered(
    request: TeamApiMailboxMarkDeliveredRequest,
) -> OmxCommandResult:
    """Marks one team mailbox message as delivered through `omx team api mailbox-mark-delivered`.

    Args:
        request [TeamApiMailboxMarkDeliveredRequest]: Typed request boundary for one mailbox delivery marker write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed mailbox-mark-delivered call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "mailbox-mark-delivered",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "worker": request.worker,
                "message_id": request.message_id,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def mark_team_mailbox_notified(
    request: TeamApiMailboxMarkNotifiedRequest,
) -> OmxCommandResult:
    """Marks one team mailbox message as notified through `omx team api mailbox-mark-notified`.

    Args:
        request [TeamApiMailboxMarkNotifiedRequest]: Typed request boundary for one mailbox notification marker write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed mailbox-mark-notified call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "mailbox-mark-notified",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "worker": request.worker,
                "message_id": request.message_id,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def write_team_shutdown_request(
    request: TeamApiWriteShutdownRequest,
) -> OmxCommandResult:
    """Writes one team shutdown request through `omx team api write-shutdown-request`.

    Args:
        request [TeamApiWriteShutdownRequest]: Typed request boundary for one team shutdown-request write.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed write-shutdown-request call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "write-shutdown-request",
        "--input",
        orjson.dumps(
            {
                "team_name": request.team_name,
                "worker": request.worker,
                "requested_by": request.requested_by,
            }
        ).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def read_team_shutdown_ack(
    request: TeamApiReadShutdownAckRequest,
) -> OmxCommandResult:
    """Reads one team shutdown ack through `omx team api read-shutdown-ack`.

    Args:
        request [TeamApiReadShutdownAckRequest]: Typed request boundary for one team shutdown-ack read.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed read-shutdown-ack call.
    """
    shutdown_ack_payload: dict[str, object] = {
        "team_name": request.team_name,
        "worker": request.worker,
    }
    if request.min_updated_at is not None:
        shutdown_ack_payload["min_updated_at"] = request.min_updated_at

    command_arguments: list[str] = [
        "team",
        "api",
        "read-shutdown-ack",
        "--input",
        orjson.dumps(shutdown_ack_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def cleanup_team_state(request: TeamApiCleanupRequest) -> OmxCommandResult:
    """Runs team cleanup through `omx team api cleanup`.

    Args:
        request [TeamApiCleanupRequest]: Typed request boundary for one team cleanup call.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed cleanup call.
    """
    cleanup_payload: dict[str, object] = {
        "team_name": request.team_name,
    }
    if request.force is not None:
        cleanup_payload["force"] = request.force
    if request.confirm_issues is not None:
        cleanup_payload["confirm_issues"] = request.confirm_issues

    command_arguments: list[str] = [
        "team",
        "api",
        "cleanup",
        "--input",
        orjson.dumps(cleanup_payload).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result


async def cleanup_team_orphans(request: TeamApiOrphanCleanupRequest) -> OmxCommandResult:
    """Runs orphan cleanup through `omx team api orphan-cleanup`.

    Args:
        request [TeamApiOrphanCleanupRequest]: Typed request boundary for one team orphan-cleanup call.

    Returns:
        OmxCommandResult: Shared OMX command-result boundary for the completed orphan-cleanup call.
    """
    command_arguments: list[str] = [
        "team",
        "api",
        "orphan-cleanup",
        "--input",
        orjson.dumps({"team_name": request.team_name}).decode(),
        "--json",
    ]
    result: OmxCommandResult = await asyncio.to_thread(run_omx_command, command_arguments)
    return result
