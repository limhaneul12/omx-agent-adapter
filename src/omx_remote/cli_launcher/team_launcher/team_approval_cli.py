import asyncio

import typer

from omx_remote.cli_launcher.omx_command_result_output import echo_omx_command_result
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiReadTaskApprovalRequest,
    TeamApiWriteTaskApprovalRequest,
)
from omx_remote.teamwork.team_api_control import (
    read_team_task_approval,
    write_team_task_approval,
)


def register_team_approval_commands(team_app: typer.Typer) -> None:
    """Register team task approval commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the approval commands.
    """

    @team_app.command("read-task-approval")
    def team_read_task_approval(
        team: str = typer.Option(..., "--team", help="Team name that owns the task."),
        task_id: str = typer.Option(..., "--task-id", help="Task id whose approval state should be read."),
    ) -> None:
        """Read one typed OMX team task approval command result.

        Args:
            team [str]: Team name that owns the task.
            task_id [str]: Task id whose approval state should be read.
        """
        result = asyncio.run(
            read_team_task_approval(
                TeamApiReadTaskApprovalRequest(team_name=team, task_id=task_id)
            )
        )
        echo_omx_command_result(result)

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
            team [str]: Team name that owns the task.
            task_id [str]: Task id whose approval state should be written.
            status [str]: Approval status to record.
            reviewer [str]: Reviewer identity writing the approval record.
            decision_reason [str]: Approval decision reason text.
            required [bool | None]: Optional required flag override.
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
        echo_omx_command_result(result)
