import asyncio

import typer

from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiClaimTaskRequest,
    TeamApiCreateTaskRequest,
    TeamApiReadTaskRequest,
    TeamApiReleaseTaskClaimRequest,
    TeamApiTransitionTaskStatusRequest,
    TeamApiUpdateTaskRequest,
)
from omx_remote.teamwork.team_api_control import (
    claim_team_task,
    create_team_task,
    read_team_task,
    release_team_task_claim,
    transition_team_task_status,
    update_team_task,
)


def register_team_task_commands(team_app: typer.Typer) -> None:
    """Register team task lifecycle commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the team task commands.
    """

    @team_app.command("create-task")
    def team_create_task(
        team: str = typer.Option(..., "--team", help="Team name that should own the task."),
        subject: str = typer.Option(..., "--subject", help="Task subject line."),
        description: str = typer.Option(..., "--description", help="Task description/body."),
        owner: str | None = typer.Option(None, "--owner", help="Optional worker owner to assign."),
    ) -> None:
        """Create one typed OMX team task.

        Args:
            team [str]: Team name that should own the task.
            subject [str]: Task subject line.
            description [str]: Task description/body.
            owner [str | None]: Optional worker owner to assign.
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
            team [str]: Team name that owns the task.
            task_id [str]: Task id to inspect.
        """
        result = asyncio.run(
            read_team_task(TeamApiReadTaskRequest(team_name=team, task_id=task_id))
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
            team [str]: Team name that owns the task.
            task_id [str]: Task id to transition.
            from_status [str]: Expected current task status.
            to_status [str]: Next task status.
            claim_token [str]: Task claim token required by OMX.
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
            team [str]: Team name that owns the task.
            task_id [str]: Task id to update.
            subject [str | None]: Updated task subject line.
            description [str | None]: Updated task description/body.
            blocked_by [list[str] | None]: Optional upstream task ids.
            requires_code_change [bool | None]: Optional code-change override.
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
            team [str]: Team name that owns the task.
            task_id [str]: Task id to claim.
            worker [str]: Worker identity claiming the task.
            expected_version [int | None]: Optional expected task version guard.
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
            team [str]: Team name that owns the task.
            task_id [str]: Task id whose claim should be released.
            claim_token [str]: Task claim token to release.
            worker [str]: Worker identity releasing the claim.
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
