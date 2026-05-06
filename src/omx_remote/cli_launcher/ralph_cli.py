import asyncio

import orjson
import typer

from omx_remote.runtime.ralph.ralph_control import (
    build_ralph_launch_plan,
    build_ralph_resume_plan,
    format_preflight_failure,
    format_resume_outcome,
)
from omx_remote.runtime.ralph.ralph_state import cleanup_ralph_state
from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStatusRequest,
    RuntimeStatusRequest,
)

ralph_app = typer.Typer(help="Read Ralph-related OMX runtime state.", add_completion=False)


def _run_omx_command(command: list[str]):
    """Run one OMX command through the public CLI facade dependency.

    Args:
        command [list[str]]: Function argument.
    """
    from omx_remote import cli as cli_facade

    return cli_facade.run_omx_command(command)


def _read_runtime_mode_state(request: RuntimeModeStateRequest):
    """Read Ralph mode state through the public CLI facade dependency.

    Args:
        request [RuntimeModeStateRequest]: Function argument.
    """
    from omx_remote import cli as cli_facade

    return cli_facade.read_runtime_mode_state(request)


def _read_runtime_mode_status(request: RuntimeModeStatusRequest):
    """Read Ralph mode status through the public CLI facade dependency.

    Args:
        request [RuntimeModeStatusRequest]: Function argument.
    """
    from omx_remote import cli as cli_facade

    return cli_facade.read_runtime_mode_status(request)


@ralph_app.command("snapshot")
def ralph_snapshot() -> None:
    """Read the current normalized runtime snapshot and inspect Ralph-related state."""
    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))
    typer.echo(result.model_dump_json(indent=2))


@ralph_app.command("startability")
def ralph_startability() -> None:
    """Read Ralph mode state and mode status to assess whether Ralph can be inspected or resumed safely."""
    mode_state = asyncio.run(_read_runtime_mode_state(RuntimeModeStateRequest(mode="ralph")))
    mode_status = asyncio.run(_read_runtime_mode_status(RuntimeModeStatusRequest(mode="ralph")))
    output_payload = {
        "mode_state": mode_state.model_dump(mode="json"),
        "mode_status": mode_status.model_dump(mode="json"),
    }
    typer.echo(orjson.dumps(output_payload, option=orjson.OPT_INDENT_2).decode())


@ralph_app.command("launch")
def ralph_launch(
    task: str = typer.Option(..., "--task", help="Task text to pass to omx ralph --prd."),
    force_cleanup: bool = typer.Option(
        False,
        "--force-cleanup",
        help="Allow launch to proceed even when known Ralph state files already exist.",
    ),
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow launch from a non-interactive stdin environment when you know upstream behavior is acceptable.",
    ),
) -> None:
    """Launch Ralph through the OMX CLI PRD-gated startup path.
    
    Args:
        task [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
    """
    try:
        command, preflight_warnings = build_ralph_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
        )
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = _run_omx_command(command)
    typer.echo(command_result.model_dump_json(indent=2))


@ralph_app.command("resume")
def ralph_resume() -> None:
    """Resume Ralph through the OMX CLI runtime surface."""
    try:
        command, preflight_warnings = build_ralph_resume_plan()
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = _run_omx_command(command)
    command_result = format_resume_outcome(command_result)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ralph_app.command("cleanup-stale")
def ralph_cleanup_stale() -> None:
    """Remove common stale Ralph state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ralph_state()
    typer.echo({"removed": removed_paths})
