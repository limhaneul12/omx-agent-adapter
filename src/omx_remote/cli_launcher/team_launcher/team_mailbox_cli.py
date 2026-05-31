import asyncio

import typer

from omx_remote.cli_launcher.omx_command_result_output import echo_omx_command_result
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiMailboxMarkDeliveredRequest,
    TeamApiMailboxMarkNotifiedRequest,
)
from omx_remote.teamwork.team_api_control import (
    mark_team_mailbox_delivered,
    mark_team_mailbox_notified,
)


def register_team_mailbox_commands(team_app: typer.Typer) -> None:
    """Register team mailbox hygiene commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the mailbox commands.
    """

    @team_app.command("mailbox-mark-delivered")
    def team_mailbox_mark_delivered(
        team: str = typer.Option(..., "--team", help="Team name that owns the mailbox."),
        worker: str = typer.Option(..., "--worker", help="Worker identity that owns the mailbox message."),
        message_id: str = typer.Option(..., "--message-id", help="Mailbox message id to mark as delivered."),
    ) -> None:
        """Mark one typed OMX mailbox message as delivered.

        Args:
            team [str]: Team name that owns the mailbox.
            worker [str]: Worker identity that owns the mailbox message.
            message_id [str]: Mailbox message id to mark as delivered.
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
        echo_omx_command_result(result)

    @team_app.command("mailbox-mark-notified")
    def team_mailbox_mark_notified(
        team: str = typer.Option(..., "--team", help="Team name that owns the mailbox."),
        worker: str = typer.Option(..., "--worker", help="Worker identity that owns the mailbox message."),
        message_id: str = typer.Option(..., "--message-id", help="Mailbox message id to mark as notified."),
    ) -> None:
        """Mark one typed OMX mailbox message as notified.

        Args:
            team [str]: Team name that owns the mailbox.
            worker [str]: Worker identity that owns the mailbox message.
            message_id [str]: Mailbox message id to mark as notified.
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
        echo_omx_command_result(result)
