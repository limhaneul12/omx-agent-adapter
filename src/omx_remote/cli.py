import asyncio

import typer
from pydantic import ValidationError

from omx_remote.bridge.adapter_envelope import read_adapter_envelope
from omx_remote.bridge.adapter_probe import probe_adapter
from omx_remote.bridge.adapter_status import read_adapter_status
from omx_remote.execution.invoke import run_omx_command
from omx_remote.history.session_search import search_sessions
from omx_remote.runtime.goal.codex_goal_runtime import (
    read_codex_goal_status,
    start_codex_goal,
)
from omx_remote.runtime.goal.codex_goal_supervisor import (
    prepare_tracked_codex_goal_ralph_handoff_prompt,
)
from omx_remote.runtime.ralph.ralph_control import (
    build_ralph_launch_plan,
    build_ralph_resume_plan,
    format_preflight_failure,
    format_resume_outcome,
)
from omx_remote.runtime.ralph.ralph_state import cleanup_ralph_state
from omx_remote.runtime.status.active_runtime_modes import read_active_runtime_modes
from omx_remote.runtime.status.runtime_mode_state import read_runtime_mode_state
from omx_remote.runtime.status.runtime_mode_status import read_runtime_mode_status
from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.runtime.ultrawork.ultrawork_control import (
    build_ultrawork_launch_plan,
    build_ultrawork_resume_plan,
    cleanup_ultrawork_state,
    format_preflight_failure as format_ultrawork_preflight_failure,
    format_resume_outcome as format_ultrawork_resume_outcome,
)
from omx_remote.schemas.bridge.adapter_schemas import AdapterProbeRequest
from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalExecutionShape,
    CodexGoalLaunchRequest,
    CodexGoalReviewPolicy,
    CodexGoalSpawnStatus,
)
from omx_remote.schemas.history.session_schemas import SessionSearchRequest
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStatusRequest,
    RuntimeStatusRequest,
)
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

HELP_TEXT = """Agent-facing adapter layer for operating OMX as a stateful runtime.

Supported commands expose currently implemented read-oriented OMX surfaces.
Use subcommand --help to see available operations for each domain.
"""

app = typer.Typer(help=HELP_TEXT, add_completion=False)
runtime_app = typer.Typer(help="Read OMX runtime and mode state.", add_completion=False)
team_app = typer.Typer(help="Read OMX team runtime and team API state.", add_completion=False)
history_app = typer.Typer(help="Read OMX session history search results.", add_completion=False)
adapt_app = typer.Typer(help="Read OMX adapter probe, status, and envelope surfaces.", add_completion=False)
goal_app = typer.Typer(help="Start and inspect adapter-tracked native Codex Goal sessions.", add_completion=False)
ralph_app = typer.Typer(help="Read Ralph-related OMX runtime state.", add_completion=False)
ultrawork_app = typer.Typer(help="Read/operate Ultrawork-related OMX runtime state.", add_completion=False)

app.add_typer(runtime_app, name="runtime")
app.add_typer(team_app, name="team")
app.add_typer(history_app, name="history")
app.add_typer(adapt_app, name="adapt")
app.add_typer(goal_app, name="goal")
app.add_typer(ralph_app, name="ralph")
app.add_typer(ultrawork_app, name="ultrawork")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show the top-level help when no subcommand is provided.
    
    Args:
        ctx [typer.Context]: Function argument.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Show the current package version."""
    typer.echo("agent-remote 0.1.0")



def _parse_goal_execution_shape(
    execution_shape_text: str,
) -> CodexGoalExecutionShape:
    """Handles parse goal execution shape.
    
    Args:
        execution_shape_text [str]: Function argument.
    
    Returns:
        CodexGoalExecutionShape: Function return value.
    """
    if execution_shape_text == "goal_only":
        execution_shape: CodexGoalExecutionShape = CodexGoalExecutionShape.GOAL_ONLY
        return execution_shape
    if execution_shape_text == "ralph_pipeline":
        execution_shape = CodexGoalExecutionShape.RALPH_PIPELINE
        return execution_shape

    raise ValueError(
        "execution_shape must be one of: goal_only, ralph_pipeline"
    )



def _parse_goal_review_policy(
    review_policy_text: str,
) -> CodexGoalReviewPolicy:
    """Handles parse goal review policy.
    
    Args:
        review_policy_text [str]: Function argument.
    
    Returns:
        CodexGoalReviewPolicy: Function return value.
    """
    if review_policy_text == "continue_automatically":
        review_policy: CodexGoalReviewPolicy = (
            CodexGoalReviewPolicy.CONTINUE_AUTOMATICALLY
        )
        return review_policy
    if review_policy_text == "review_required":
        review_policy = CodexGoalReviewPolicy.REVIEW_REQUIRED
        return review_policy

    raise ValueError(
        "review_policy must be one of: continue_automatically, review_required"
    )


@goal_app.command("start")
def goal_start(
    objective: str = typer.Option(..., "--objective", help="Goal objective text to inject into native Codex Goal."),
    execution_shape: str = typer.Option(
        "goal_only",
        "--execution-shape",
        help="Adapter-owned execution shape for the tracked goal session.",
    ),
    review_policy: str = typer.Option(
        "continue_automatically",
        "--review-policy",
        help="Adapter-owned Ralph PRD review policy for later handoff.",
    ),
    team_worker_count: int | None = typer.Option(
        None,
        "--team-worker-count",
        help="Optional Team worker count to carry for Ralph-pipeline handoff.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory where Codex should start and mirror state should be written.",
    ),
) -> None:
    """Start one adapter-tracked native Codex Goal session.
    
    Args:
        objective [str]: Function argument.
        execution_shape [str]: Function argument.
        review_policy [str]: Function argument.
        team_worker_count [int | None]: Function argument.
        cwd [str | None]: Function argument.
    """
    try:
        parsed_execution_shape: CodexGoalExecutionShape = _parse_goal_execution_shape(
            execution_shape
        )
        parsed_review_policy: CodexGoalReviewPolicy = _parse_goal_review_policy(
            review_policy
        )
        request = CodexGoalLaunchRequest(
            objective_text=objective,
            execution_shape=parsed_execution_shape,
            review_policy=parsed_review_policy,
            team_worker_count=team_worker_count,
            working_directory=cwd,
        )
        result = start_codex_goal(request)
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))
    if result.spawn_result.spawn_status != CodexGoalSpawnStatus.STARTED:
        raise typer.Exit(code=1)


@goal_app.command("status")
def goal_status(
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose adapter-owned goal mirror state should be read.",
    ),
) -> None:
    """Read the latest adapter-owned native Codex Goal mirror state.
    
    Args:
        cwd [str | None]: Function argument.
    """
    try:
        result = read_codex_goal_status(working_directory=cwd)
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))


@goal_app.command("prepare-ralph")
def goal_prepare_ralph(
    source_paths: list[str] | None = typer.Option(
        None,
        "--source-path",
        help="Source path Ralph must read. Pass multiple times for multiple paths.",
    ),
    requested_slice: str = typer.Option(
        ...,
        "--requested-slice",
        help="One implementation slice Ralph should structure into a PRD artifact.",
    ),
    constraints: list[str] | None = typer.Option(
        None,
        "--constraint",
        help="Constraint Ralph must preserve. Pass multiple times for multiple constraints.",
    ),
    verification_expectations: list[str] | None = typer.Option(
        None,
        "--verification-expectation",
        help="Verification gate Ralph must include. Pass multiple times for multiple gates.",
    ),
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory whose adapter-owned goal mirror state should be read.",
    ),
) -> None:
    """Prepare a read-only Ralph PRD handoff prompt from the tracked Goal.
    
    Args:
        source_paths [list[str] | None]: Function argument.
        requested_slice [str]: Function argument.
        constraints [list[str] | None]: Function argument.
        verification_expectations [list[str] | None]: Function argument.
        cwd [str | None]: Function argument.
    """
    try:
        result = prepare_tracked_codex_goal_ralph_handoff_prompt(
            working_directory=cwd,
            source_paths=tuple([] if source_paths is None else source_paths),
            requested_slice=requested_slice,
            constraints=tuple([] if constraints is None else constraints),
            verification_expectations=tuple(
                []
                if verification_expectations is None
                else verification_expectations
            ),
        )
    except (ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("status")
def runtime_status() -> None:
    """Read normalized OMX runtime status."""
    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("active-modes")
def runtime_active_modes() -> None:
    """Read active OMX runtime modes."""
    result = asyncio.run(read_active_runtime_modes())
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("mode-status")
def runtime_mode_status(mode: str = typer.Option(..., "--mode", help="OMX mode name to inspect.")) -> None:
    """Read normalized OMX state get-status result for one mode.
    
    Args:
        mode [str]: Function argument.
    """
    result = asyncio.run(read_runtime_mode_status(RuntimeModeStatusRequest(mode=mode)))
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("mode-state")
def runtime_mode_state(mode: str = typer.Option(..., "--mode", help="OMX mode name to inspect.")) -> None:
    """Read normalized OMX state read result for one mode.
    
    Args:
        mode [str]: Function argument.
    """
    result = asyncio.run(read_runtime_mode_state(RuntimeModeStateRequest(mode=mode)))
    typer.echo(result.model_dump_json(indent=2))


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


@history_app.command("session-search")
def history_session_search(
    query: str = typer.Option(..., "--query", help="Search query to run against OMX session history."),
    limit: int = typer.Option(10, "--limit", help="Maximum number of results to return."),
) -> None:
    """Read normalized OMX session-search results.
    
    Args:
        query [str]: Function argument.
        limit [int]: Function argument.
    """
    result = asyncio.run(search_sessions(SessionSearchRequest(query=query, limit=limit)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("probe")
def adapt_probe(target: str = typer.Option(..., "--target", help="Adapter target name to inspect.")) -> None:
    """Read normalized OMX adapter probe output.
    
    Args:
        target [str]: Function argument.
    """
    result = asyncio.run(probe_adapter(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("status")
def adapt_status(target: str = typer.Option(..., "--target", help="Adapter target name to inspect.")) -> None:
    """Read normalized OMX adapter status output.
    
    Args:
        target [str]: Function argument.
    """
    result = asyncio.run(read_adapter_status(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("envelope")
def adapt_envelope(target: str = typer.Option(..., "--target", help="Adapter target name to inspect.")) -> None:
    """Read normalized OMX adapter envelope output.
    
    Args:
        target [str]: Function argument.
    """
    result = asyncio.run(read_adapter_envelope(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@ralph_app.command("snapshot")
def ralph_snapshot() -> None:
    """Read the current normalized runtime snapshot and inspect Ralph-related state."""
    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))
    typer.echo(result.model_dump_json(indent=2))


@ralph_app.command("startability")
def ralph_startability() -> None:
    """Read Ralph mode state and mode status to assess whether Ralph can be inspected or resumed safely."""
    mode_state = asyncio.run(read_runtime_mode_state(RuntimeModeStateRequest(mode="ralph")))
    mode_status = asyncio.run(read_runtime_mode_status(RuntimeModeStatusRequest(mode="ralph")))
    typer.echo(
        {
            "mode_state": mode_state.model_dump(),
            "mode_status": mode_status.model_dump(),
        }
    )


@ralph_app.command("launch")
def ralph_launch(
    task: str = typer.Option(..., "--task", help="Task text to pass to omx ralph --prd."),
    force_cleanup: bool = typer.Option(
        False,
        "--force-cleanup",
        help="Allow launch to proceed even when known Ralph state files already exist.",
    ),
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow launch from a non-interactive stdin environment when you know upstream behavior is acceptable.",
    ),
) -> None:
    """Launch Ralph through the OMX CLI PRD-gated startup path.
    
    Args:
        task [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
    """
    try:
        command, preflight_warnings = build_ralph_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
        )
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = run_omx_command(command)
    typer.echo(command_result.model_dump_json(indent=2))


@ralph_app.command("resume")
def ralph_resume() -> None:
    """Resume Ralph through the OMX CLI runtime surface."""
    try:
        command, preflight_warnings = build_ralph_resume_plan()
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = run_omx_command(command)
    command_result = format_resume_outcome(command_result)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ralph_app.command("cleanup-stale")
def ralph_cleanup_stale() -> None:
    """Remove common stale Ralph state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ralph_state()
    typer.echo({"removed": removed_paths})


@ultrawork_app.command("launch")
def ultrawork_launch(
    task: str = typer.Option(..., "--task", help="Task text to pass to `omx team [N:role] \"<task>\"`."),
    team_size: int = typer.Option(
        1,
        "--team-size",
        help="Team size to allocate for the task (defaults to 1).",
    ),
    team_role: str = typer.Option(
        "executor",
        "--team-role",
        help="Team worker role to use for the launch prefix (defaults to executor).",
    ),
    force_cleanup: bool = typer.Option(
        False,
        "--force-cleanup",
        help="Allow launch to proceed even when known Ultrawork state files already exist.",
    ),
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow launch from a non-interactive stdin environment when you know upstream behavior is acceptable.",
    ),
) -> None:
    """Launch Ultrawork through `omx team [N:role]` with state-aware guardrails.
    
    Args:
        task [str]: Function argument.
        team_size [int]: Function argument.
        team_role [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
    """
    try:
        command, preflight_warnings = build_ultrawork_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
            team_size=team_size,
            team_role=team_role,
        )
    except ValueError as error:
        command_result = format_ultrawork_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = run_omx_command(command)
    typer.echo(command_result.model_dump_json(indent=2))


@ultrawork_app.command("resume")
def ultrawork_resume(
    team_name: str = typer.Option(..., "--team-name", help="Team name to resume."),
) -> None:
    """Resume Ultrawork through `omx team resume <team-name>`.
    
    Args:
        team_name [str]: Function argument.
    """
    try:
        command, preflight_warnings = build_ultrawork_resume_plan(team_name)
    except ValueError as error:
        command_result = format_ultrawork_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = run_omx_command(command)
    command_result = format_ultrawork_resume_outcome(command_result, team_name=team_name)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ultrawork_app.command("cleanup-stale")
def ultrawork_cleanup_stale() -> None:
    """Remove common stale Ultrawork state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ultrawork_state()
    typer.echo({"removed": removed_paths})


if __name__ == "__main__":
    app()
