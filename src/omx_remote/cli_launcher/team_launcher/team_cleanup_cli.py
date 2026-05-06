import asyncio

import typer

from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiCleanupRequest,
    TeamApiOrphanCleanupRequest,
)
from omx_remote.teamwork.team_api_control import (
    cleanup_team_orphans,
    cleanup_team_state,
)


def register_team_cleanup_commands(team_app: typer.Typer) -> None:
    """Register team cleanup commands.

    Args:
        team_app [typer.Typer]: Typer app receiving the cleanup commands.
    """

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
            team [str]: Team name whose runtime state should be cleaned up.
            force [bool | None]: Optional force flag override.
            confirm_issues [bool | None]: Optional failed-task acknowledgement override.
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
            team [str]: Team name whose orphaned runtime state should be cleaned up.
        """
        result = asyncio.run(
            cleanup_team_orphans(TeamApiOrphanCleanupRequest(team_name=team))
        )
        typer.echo(result.model_dump_json(indent=2))
        if result.exit_code != 0:
            raise typer.Exit(code=result.exit_code)
