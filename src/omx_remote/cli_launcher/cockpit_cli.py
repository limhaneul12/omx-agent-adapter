import asyncio
import os
from pathlib import Path

import typer

from omx_remote.runtime.cockpit.snapshot.reader import read_cockpit_snapshot
from omx_remote.schemas.cockpit.snapshot_schemas import CockpitSnapshotRequest

cockpit_app = typer.Typer(
    help="Read one repo-scoped cockpit snapshot across operating lanes.",
    add_completion=False,
)


@cockpit_app.command("snapshot")
def cockpit_snapshot(
    cwd: str = typer.Option(".", "--cwd", help="Workspace root to inspect."),
    team_names: list[str] | None = typer.Option(
        None,
        "--team",
        "--team-name",
        help="Optional explicit Team name to include in the Ralph -> Team lane.",
    ),
) -> None:
    """Read the repo-scoped cockpit snapshot as JSON.

    Args:
        cwd [str]: Workspace root to inspect.
        team_names [list[str] | None]: Optional explicit Team names to include in the snapshot.
    """
    repo_root: str = str(Path(cwd).resolve())
    normalized_team_names: tuple[str, ...]
    if team_names is None:
        normalized_team_names = ()
    else:
        normalized_team_names = tuple(team_names)

    request = CockpitSnapshotRequest(
        repo_root=repo_root,
        team_names=normalized_team_names,
    )
    previous_cwd: str = os.getcwd()
    try:
        os.chdir(repo_root)
        result = asyncio.run(read_cockpit_snapshot(request))
    finally:
        os.chdir(previous_cwd)

    typer.echo(result.model_dump_json(indent=2))
