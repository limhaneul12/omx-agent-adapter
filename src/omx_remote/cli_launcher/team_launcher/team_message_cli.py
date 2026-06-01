import asyncio

import typer

from omx_remote.cli_launcher.omx_command_result_output import echo_omx_command_result
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiBroadcastRequest,
    TeamApiSendMessageRequest,
    TeamApiWorkerInboxWriteRequest,
)
from omx_remote.teamwork.team_api_control import (
    broadcast_team_message,
    send_team_message,
    write_team_worker_inbox,
)


def register_team_message_commands(team_app: typer.Typer) -> None:
    """Register team message and inbox commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the team message commands.
    """

    @team_app.command("send-message")
    def team_send_message(
        team: str = typer.Option(
            ..., "--team", help="Team name that owns the mailbox lane."
        ),
        from_worker: str = typer.Option(
            ..., "--from-worker", help="Worker identity sending the message."
        ),
        to_worker: str = typer.Option(
            ..., "--to-worker", help="Worker identity receiving the message."
        ),
        body: str = typer.Option(..., "--body", help="Message body to deliver."),
    ) -> None:
        """Send one typed OMX team message.

        Args:
            team [str]: Team name that owns the mailbox lane.
            from_worker [str]: Worker identity sending the message.
            to_worker [str]: Worker identity receiving the message.
            body [str]: Message body to deliver.
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
        echo_omx_command_result(result)

    @team_app.command("write-inbox")
    def team_write_inbox(
        team: str = typer.Option(
            ..., "--team", help="Team name that owns the worker inbox."
        ),
        worker: str = typer.Option(
            ..., "--worker", help="Worker identity whose inbox should be updated."
        ),
        content: str = typer.Option(..., "--content", help="Inbox content to write."),
    ) -> None:
        """Write one typed OMX worker inbox entry.

        Args:
            team [str]: Team name that owns the worker inbox.
            worker [str]: Worker identity whose inbox should be updated.
            content [str]: Inbox content to write.
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
        echo_omx_command_result(result)

    @team_app.command("broadcast")
    def team_broadcast(
        team: str = typer.Option(
            ..., "--team", help="Team name that should receive the broadcast."
        ),
        from_worker: str = typer.Option(
            ..., "--from-worker", help="Worker identity sending the broadcast."
        ),
        body: str = typer.Option(..., "--body", help="Broadcast body to deliver."),
    ) -> None:
        """Broadcast one typed OMX team message.

        Args:
            team [str]: Team name that should receive the broadcast.
            from_worker [str]: Worker identity sending the broadcast.
            body [str]: Broadcast body to deliver.
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
        echo_omx_command_result(result)
