import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.runtime.next.next_action_reader import read_next_action
from omx_remote.schemas.next.next_action_schemas import (
    NextActionRequest,
    NextActionResult,
)


def next_command(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root to inspect.",
    ),
    task: str | None = typer.Option(
        None,
        "--task",
        help="Optional task text used for route recommendation.",
    ),
    team_names: list[str] | None = typer.Option(
        None,
        "--team",
        "--team-name",
        help="Optional Team name to include in cockpit evidence.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed next-action result as JSON.",
    ),
) -> None:
    """Recommend the next safe read-only action for this repo.

    Args:
        cwd [Path]: Repository root to inspect.
        task [str | None]: Optional task text for route policy.
        team_names [list[str] | None]: Optional explicit Team names to inspect.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        normalized_team_names: tuple[str, ...]
        if team_names is None:
            normalized_team_names = ()
        else:
            normalized_team_names = tuple(team_names)
        request = NextActionRequest(
            repo_root=str(cwd.resolve()),
            task=task,
            team_names=normalized_team_names,
        )
        result: NextActionResult = asyncio.run(read_next_action(request))
    except (OSError, ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"recommended_action: {result.recommended_action}")
    typer.echo(f"safe_to_mutate: {str(result.safe_to_mutate).lower()}")
    typer.echo(f"requires_review: {str(result.requires_review).lower()}")
    typer.echo(f"summary: {result.summary}")
    for why in result.why:
        typer.echo(f"why: {why}")
    for command in result.recommended_commands:
        typer.echo(f"recommended_command: {command}")
    for blocked_action in result.blocked_actions:
        typer.echo(f"blocked_action: {blocked_action}")
