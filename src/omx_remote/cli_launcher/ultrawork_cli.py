import typer

from omx_remote.runtime.ultrawork.ultrawork_control import (
    build_ultrawork_launch_plan,
    build_ultrawork_resume_plan,
    cleanup_ultrawork_state,
    format_preflight_failure as format_ultrawork_preflight_failure,
    format_resume_outcome as format_ultrawork_resume_outcome,
)

ultrawork_app = typer.Typer(help="Read/operate Ultrawork-related OMX runtime state.", add_completion=False)


def _run_omx_command(command: list[str]):
    """Run one OMX command through the public CLI facade dependency.

    Args:
        command [list[str]]: Function argument.
    """
    from omx_remote import cli as cli_facade

    return cli_facade.run_omx_command(command)


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

    command_result = _run_omx_command(command)
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

    command_result = _run_omx_command(command)
    command_result = format_ultrawork_resume_outcome(command_result, team_name=team_name)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ultrawork_app.command("cleanup-stale")
def ultrawork_cleanup_stale() -> None:
    """Remove common stale Ultrawork state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ultrawork_state()
    typer.echo({"removed": removed_paths})
