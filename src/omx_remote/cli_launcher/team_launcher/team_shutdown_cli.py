import asyncio

import typer

from omx_remote.cli_launcher.omx_command_result_output import echo_omx_command_result
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiReadShutdownAckRequest,
    TeamApiWriteShutdownRequest,
)
from omx_remote.teamwork.team_api_control import (
    read_team_shutdown_ack,
    write_team_shutdown_request,
)


def register_team_shutdown_commands(team_app: typer.Typer) -> None:
    """Register team shutdown coordination commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the shutdown commands.
    """

    @team_app.command("write-shutdown-request")
    def team_write_shutdown_request(
        team: str = typer.Option(
            ..., "--team", help="Team name that owns the worker shutdown lane."
        ),
        worker: str = typer.Option(
            ..., "--worker", help="Worker identity receiving the shutdown request."
        ),
        requested_by: str = typer.Option(
            ...,
            "--requested-by",
            help="Requester identity writing the shutdown request.",
        ),
    ) -> None:
        """Write one typed OMX team shutdown request.

        Args:
            team [str]: Team name that owns the worker shutdown lane.
            worker [str]: Worker identity receiving the shutdown request.
            requested_by [str]: Requester identity writing the request.
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
        echo_omx_command_result(result)

    @team_app.command("read-shutdown-ack")
    def team_read_shutdown_ack(
        team: str = typer.Option(
            ..., "--team", help="Team name that owns the worker shutdown lane."
        ),
        worker: str = typer.Option(
            ..., "--worker", help="Worker identity whose shutdown ack should be read."
        ),
        min_updated_at: str | None = typer.Option(
            None, "--min-updated-at", help="Optional minimum ack updated_at watermark."
        ),
    ) -> None:
        """Read one typed OMX team shutdown ack command result.

        Args:
            team [str]: Team name that owns the worker shutdown lane.
            worker [str]: Worker identity whose shutdown ack should be read.
            min_updated_at [str | None]: Optional minimum ack updated_at watermark.
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
        echo_omx_command_result(result)
