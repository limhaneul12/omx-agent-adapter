import asyncio

import typer

from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiBroadcastRequest,
    TeamApiClaimTaskRequest,
    TeamApiCleanupRequest,
    TeamApiCreateTaskRequest,
    TeamApiListTasksRequest,
    TeamApiMailboxMarkDeliveredRequest,
    TeamApiMailboxMarkNotifiedRequest,
    TeamApiOrphanCleanupRequest,
    TeamApiReadEventsRequest,
    TeamApiReadShutdownAckRequest,
    TeamApiReadTaskApprovalRequest,
    TeamApiReadTaskRequest,
    TeamApiReadWorkerStatusRequest,
    TeamApiReleaseTaskClaimRequest,
    TeamApiSendMessageRequest,
    TeamApiTransitionTaskStatusRequest,
    TeamApiUpdateTaskRequest,
    TeamApiWorkerInboxWriteRequest,
    TeamApiWriteShutdownRequest,
    TeamApiWriteTaskApprovalRequest,
)
from omx_remote.schemas.teamwork.status_schemas import (
    TeamAwaitRequest,
    TeamStatusRequest,
)
from omx_remote.teamwork.team_api_control import (
    broadcast_team_message,
    claim_team_task,
    cleanup_team_orphans,
    cleanup_team_state,
    create_team_task,
    mark_team_mailbox_delivered,
    mark_team_mailbox_notified,
    read_team_shutdown_ack,
    read_team_task,
    read_team_task_approval,
    release_team_task_claim,
    send_team_message,
    transition_team_task_status,
    update_team_task,
    write_team_shutdown_request,
    write_team_task_approval,
    write_team_worker_inbox,
)
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
    read_team_api_read_worker_status,
)
from omx_remote.teamwork.team_snapshot import await_team_status, read_team_status

team_app = typer.Typer(help="Read OMX team runtime and team API state.", add_completion=False)


@team_app.command("status")
def team_status(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
    """Read normalized OMX team status.
    
    Args:
        team [str]: Function argument.
    """
    result = asyncio.run(read_team_status(TeamStatusRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("await-event")
def team_await_event(
    team: str = typer.Option(..., "--team", help="Team name to inspect."),
    timeout_ms: int = typer.Option(1000, "--timeout-ms", help="Wait timeout in milliseconds."),
) -> None:
    """Read one normalized OMX team await snapshot.
    
    Args:
        team [str]: Function argument.
        timeout_ms [int]: Function argument.
    """
    _ = timeout_ms
    result = asyncio.run(await_team_status(TeamAwaitRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("tasks")
def team_tasks(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
    """Read normalized OMX team task list.
    
    Args:
        team [str]: Function argument.
    """
    result = asyncio.run(read_team_api_list_tasks(TeamApiListTasksRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("events")
def team_events(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
    """Read normalized OMX team event list.
    
    Args:
        team [str]: Function argument.
    """
    result = asyncio.run(read_team_api_read_events(TeamApiReadEventsRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("worker-status")
def team_worker_status(
    team: str = typer.Option(..., "--team", help="Team name to inspect."),
    worker: str = typer.Option(..., "--worker", help="Worker name to inspect."),
) -> None:
    """Read normalized OMX team worker status.
    
    Args:
        team [str]: Function argument.
        worker [str]: Function argument.
    """
    result = asyncio.run(
        read_team_api_read_worker_status(
            TeamApiReadWorkerStatusRequest(team_name=team, worker=worker)
        )
    )
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("send-message")
def team_send_message(
    team: str = typer.Option(..., "--team", help="Team name that owns the mailbox lane."),
    from_worker: str = typer.Option(..., "--from-worker", help="Worker identity sending the message."),
    to_worker: str = typer.Option(..., "--to-worker", help="Worker identity receiving the message."),
    body: str = typer.Option(..., "--body", help="Message body to deliver."),
) -> None:
    """Send one typed OMX team message.
    
    Args:
        team [str]: Function argument.
        from_worker [str]: Function argument.
        to_worker [str]: Function argument.
        body [str]: Function argument.
    """
    result = asyncio.run(
        send_team_message(
            TeamApiSendMessageRequest(
                team_name=team,
                from_worker=from_worker,
                to_worker=to_worker,
                body=body,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("write-inbox")
def team_write_inbox(
    team: str = typer.Option(..., "--team", help="Team name that owns the worker inbox."),
    worker: str = typer.Option(..., "--worker", help="Worker identity whose inbox should be updated."),
    content: str = typer.Option(..., "--content", help="Inbox content to write."),
) -> None:
    """Write one typed OMX worker inbox entry.
    
    Args:
        team [str]: Function argument.
        worker [str]: Function argument.
        content [str]: Function argument.
    """
    result = asyncio.run(
        write_team_worker_inbox(
            TeamApiWorkerInboxWriteRequest(
                team_name=team,
                worker=worker,
                content=content,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("broadcast")
def team_broadcast(
    team: str = typer.Option(..., "--team", help="Team name that should receive the broadcast."),
    from_worker: str = typer.Option(..., "--from-worker", help="Worker identity sending the broadcast."),
    body: str = typer.Option(..., "--body", help="Broadcast body to deliver."),
) -> None:
    """Broadcast one typed OMX team message.
    
    Args:
        team [str]: Function argument.
        from_worker [str]: Function argument.
        body [str]: Function argument.
    """
    result = asyncio.run(
        broadcast_team_message(
            TeamApiBroadcastRequest(
                team_name=team,
                from_worker=from_worker,
                body=body,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("create-task")
def team_create_task(
    team: str = typer.Option(..., "--team", help="Team name that should own the task."),
    subject: str = typer.Option(..., "--subject", help="Task subject line."),
    description: str = typer.Option(..., "--description", help="Task description/body."),
    owner: str | None = typer.Option(None, "--owner", help="Optional worker owner to assign."),
) -> None:
    """Create one typed OMX team task.
    
    Args:
        team [str]: Function argument.
        subject [str]: Function argument.
        description [str]: Function argument.
        owner [str | None]: Function argument.
    """
    result = asyncio.run(
        create_team_task(
            TeamApiCreateTaskRequest(
                team_name=team,
                subject=subject,
                description=description,
                owner=owner,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("read-task")
def team_read_task(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id to inspect."),
) -> None:
    """Read one typed OMX team task command result.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
    """
    result = asyncio.run(
        read_team_task(
            TeamApiReadTaskRequest(
                team_name=team,
                task_id=task_id,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("transition-task-status")
def team_transition_task_status(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id to transition."),
    from_status: str = typer.Option(..., "--from-status", help="Expected current task status."),
    to_status: str = typer.Option(..., "--to-status", help="Next task status."),
    claim_token: str = typer.Option(..., "--claim-token", help="Task claim token required by OMX."),
) -> None:
    """Transition one typed OMX team task status.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
        from_status [str]: Function argument.
        to_status [str]: Function argument.
        claim_token [str]: Function argument.
    """
    result = asyncio.run(
        transition_team_task_status(
            TeamApiTransitionTaskStatusRequest(
                team_name=team,
                task_id=task_id,
                from_status=from_status,
                to_status=to_status,
                claim_token=claim_token,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("update-task")
def team_update_task(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id to update."),
    subject: str | None = typer.Option(None, "--subject", help="Updated task subject line."),
    description: str | None = typer.Option(None, "--description", help="Updated task description/body."),
    blocked_by: list[str] | None = typer.Option(None, "--blocked-by", help="Optional upstream task ids that block this task."),
    requires_code_change: bool | None = typer.Option(
        None,
        "--requires-code-change/--no-requires-code-change",
        help="Optional requires_code_change boolean override.",
    ),
) -> None:
    """Update one typed OMX team task metadata record.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
        subject [str | None]: Function argument.
        description [str | None]: Function argument.
        blocked_by [list[str] | None]: Function argument.
        requires_code_change [bool | None]: Function argument.
    """
    result = asyncio.run(
        update_team_task(
            TeamApiUpdateTaskRequest(
                team_name=team,
                task_id=task_id,
                subject=subject,
                description=description,
                blocked_by=blocked_by,
                requires_code_change=requires_code_change,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("claim-task")
def team_claim_task(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id to claim."),
    worker: str = typer.Option(..., "--worker", help="Worker identity claiming the task."),
    expected_version: int | None = typer.Option(None, "--expected-version", help="Optional expected task version guard."),
) -> None:
    """Claim one typed OMX team task.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
        worker [str]: Function argument.
        expected_version [int | None]: Function argument.
    """
    result = asyncio.run(
        claim_team_task(
            TeamApiClaimTaskRequest(
                team_name=team,
                task_id=task_id,
                worker=worker,
                expected_version=expected_version,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("release-task-claim")
def team_release_task_claim(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id whose claim should be released."),
    claim_token: str = typer.Option(..., "--claim-token", help="Task claim token to release."),
    worker: str = typer.Option(..., "--worker", help="Worker identity releasing the claim."),
) -> None:
    """Release one typed OMX team task claim.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
        claim_token [str]: Function argument.
        worker [str]: Function argument.
    """
    result = asyncio.run(
        release_team_task_claim(
            TeamApiReleaseTaskClaimRequest(
                team_name=team,
                task_id=task_id,
                claim_token=claim_token,
                worker=worker,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("read-task-approval")
def team_read_task_approval(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id whose approval state should be read."),
) -> None:
    """Read one typed OMX team task approval command result.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
    """
    result = asyncio.run(
        read_team_task_approval(
            TeamApiReadTaskApprovalRequest(
                team_name=team,
                task_id=task_id,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("write-task-approval")
def team_write_task_approval(
    team: str = typer.Option(..., "--team", help="Team name that owns the task."),
    task_id: str = typer.Option(..., "--task-id", help="Task id whose approval state should be written."),
    status: str = typer.Option(..., "--status", help="Approval status to record."),
    reviewer: str = typer.Option(..., "--reviewer", help="Reviewer identity writing the approval record."),
    decision_reason: str = typer.Option(..., "--decision-reason", help="Approval decision reason text."),
    required: bool | None = typer.Option(
        None,
        "--required/--not-required",
        help="Optional required flag override.",
    ),
) -> None:
    """Write one typed OMX team task approval record.
    
    Args:
        team [str]: Function argument.
        task_id [str]: Function argument.
        status [str]: Function argument.
        reviewer [str]: Function argument.
        decision_reason [str]: Function argument.
        required [bool | None]: Function argument.
    """
    result = asyncio.run(
        write_team_task_approval(
            TeamApiWriteTaskApprovalRequest(
                team_name=team,
                task_id=task_id,
                status=status,
                reviewer=reviewer,
                decision_reason=decision_reason,
                required=required,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("mailbox-mark-delivered")
def team_mailbox_mark_delivered(
    team: str = typer.Option(..., "--team", help="Team name that owns the mailbox."),
    worker: str = typer.Option(..., "--worker", help="Worker identity that owns the mailbox message."),
    message_id: str = typer.Option(..., "--message-id", help="Mailbox message id to mark as delivered."),
) -> None:
    """Mark one typed OMX mailbox message as delivered.
    
    Args:
        team [str]: Function argument.
        worker [str]: Function argument.
        message_id [str]: Function argument.
    """
    result = asyncio.run(
        mark_team_mailbox_delivered(
            TeamApiMailboxMarkDeliveredRequest(
                team_name=team,
                worker=worker,
                message_id=message_id,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("mailbox-mark-notified")
def team_mailbox_mark_notified(
    team: str = typer.Option(..., "--team", help="Team name that owns the mailbox."),
    worker: str = typer.Option(..., "--worker", help="Worker identity that owns the mailbox message."),
    message_id: str = typer.Option(..., "--message-id", help="Mailbox message id to mark as notified."),
) -> None:
    """Mark one typed OMX mailbox message as notified.
    
    Args:
        team [str]: Function argument.
        worker [str]: Function argument.
        message_id [str]: Function argument.
    """
    result = asyncio.run(
        mark_team_mailbox_notified(
            TeamApiMailboxMarkNotifiedRequest(
                team_name=team,
                worker=worker,
                message_id=message_id,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("write-shutdown-request")
def team_write_shutdown_request(
    team: str = typer.Option(..., "--team", help="Team name that owns the worker shutdown lane."),
    worker: str = typer.Option(..., "--worker", help="Worker identity receiving the shutdown request."),
    requested_by: str = typer.Option(..., "--requested-by", help="Requester identity writing the shutdown request."),
) -> None:
    """Write one typed OMX team shutdown request.
    
    Args:
        team [str]: Function argument.
        worker [str]: Function argument.
        requested_by [str]: Function argument.
    """
    result = asyncio.run(
        write_team_shutdown_request(
            TeamApiWriteShutdownRequest(
                team_name=team,
                worker=worker,
                requested_by=requested_by,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("read-shutdown-ack")
def team_read_shutdown_ack(
    team: str = typer.Option(..., "--team", help="Team name that owns the worker shutdown lane."),
    worker: str = typer.Option(..., "--worker", help="Worker identity whose shutdown ack should be read."),
    min_updated_at: str | None = typer.Option(None, "--min-updated-at", help="Optional minimum ack updated_at watermark."),
) -> None:
    """Read one typed OMX team shutdown ack command result.
    
    Args:
        team [str]: Function argument.
        worker [str]: Function argument.
        min_updated_at [str | None]: Function argument.
    """
    result = asyncio.run(
        read_team_shutdown_ack(
            TeamApiReadShutdownAckRequest(
                team_name=team,
                worker=worker,
                min_updated_at=min_updated_at,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("cleanup")
def team_cleanup(
    team: str = typer.Option(..., "--team", help="Team name whose runtime state should be cleaned up."),
    force: bool | None = typer.Option(
        None,
        "--force/--no-force",
        help="Optional force flag override for cleanup orchestration.",
    ),
    confirm_issues: bool | None = typer.Option(
        None,
        "--confirm-issues/--no-confirm-issues",
        help="Optional failed-task acknowledgement override for cleanup orchestration.",
    ),
) -> None:
    """Run one typed OMX team cleanup call.
    
    Args:
        team [str]: Function argument.
        force [bool | None]: Function argument.
        confirm_issues [bool | None]: Function argument.
    """
    result = asyncio.run(
        cleanup_team_state(
            TeamApiCleanupRequest(
                team_name=team,
                force=force,
                confirm_issues=confirm_issues,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@team_app.command("orphan-cleanup")
def team_orphan_cleanup(
    team: str = typer.Option(..., "--team", help="Team name whose orphaned runtime state should be cleaned up."),
) -> None:
    """Run one typed OMX team orphan-cleanup call.
    
    Args:
        team [str]: Function argument.
    """
    result = asyncio.run(
        cleanup_team_orphans(
            TeamApiOrphanCleanupRequest(
                team_name=team,
            )
        )
    )
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)
