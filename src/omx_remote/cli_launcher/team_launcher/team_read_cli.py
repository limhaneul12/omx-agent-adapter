import asyncio

import typer

from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
    TeamApiReadWorkerStatusRequest,
)
from omx_remote.schemas.teamwork.status_schemas import (
    TeamAwaitRequest,
    TeamStatusRequest,
)
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
    read_team_api_read_worker_status,
)
from omx_remote.teamwork.team_snapshot import await_team_status, read_team_status


def register_team_read_commands(team_app: typer.Typer) -> None:
    """Register read-only team inspection commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the team read commands.
    """

    @team_app.command("status")
    def team_status(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
        """Read normalized OMX team status.

        Args:
            team [str]: Team name to inspect.
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
            team [str]: Team name to inspect.
            timeout_ms [int]: Wait timeout accepted for CLI compatibility.
        """
        _ = timeout_ms
        result = asyncio.run(await_team_status(TeamAwaitRequest(team_name=team)))
        typer.echo(result.model_dump_json(indent=2))

    @team_app.command("tasks")
    def team_tasks(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
        """Read normalized OMX team task list.

        Args:
            team [str]: Team name to inspect.
        """
        result = asyncio.run(read_team_api_list_tasks(TeamApiListTasksRequest(team_name=team)))
        typer.echo(result.model_dump_json(indent=2))

    @team_app.command("events")
    def team_events(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
        """Read normalized OMX team event list.

        Args:
            team [str]: Team name to inspect.
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
            team [str]: Team name to inspect.
            worker [str]: Worker name to inspect.
        """
        result = asyncio.run(
            read_team_api_read_worker_status(
                TeamApiReadWorkerStatusRequest(team_name=team, worker=worker)
            )
        )
        typer.echo(result.model_dump_json(indent=2))
