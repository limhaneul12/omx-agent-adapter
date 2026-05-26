from pathlib import Path

import orjson
import typer

from omx_remote.runtime.comx.tui_daemon_control import (
    attach_comx_tui_daemon,
    build_daemon_start_command,
    read_comx_tui_daemon_status,
    start_comx_tui_daemon,
    stop_comx_tui_daemon,
)
from omx_remote.schemas.comx.tui_daemon_schemas import (
    ComxTuiDaemonActionResult,
    ComxTuiDaemonCommandPreview,
    ComxTuiDaemonStatusResult,
)

daemon_app = typer.Typer(
    help="Run the comx-agent TUI as a durable tmux-backed background session.",
    add_completion=False,
)


def _format_error_payload(error: Exception) -> str:
    """Format one daemon CLI error as JSON.

    Args:
        error [Exception]: Error to render.

    Returns:
        str: JSON error payload.
    """
    payload: dict[str, object] = {"ok": False, "error": str(error)}
    error_payload: str = orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
    return error_payload


def _format_status_human(status: ComxTuiDaemonStatusResult) -> str:
    """Render daemon status for humans.

    Args:
        status [ComxTuiDaemonStatusResult]: Status contract.

    Returns:
        str: Human-readable status.
    """
    lines: list[str] = [
        f"state: {status.state}",
        f"tmux_session: {status.tmux_session}",
        f"tui_session_id: {status.tui_session_id}",
        f"cwd: {status.cwd}",
        f"process_id: {status.process_id or '-'}",
        f"attach: {' '.join(status.attach_command)}",
    ]
    lines.extend(f"warning: {warning}" for warning in status.warnings)
    rendered: str = "\n".join(lines)
    return rendered


def _format_action_human(result: ComxTuiDaemonActionResult) -> str:
    """Render daemon action result for humans.

    Args:
        result [ComxTuiDaemonActionResult]: Action result contract.

    Returns:
        str: Human-readable action result.
    """
    lines: list[str] = [
        f"action: {result.action}",
        f"state: {result.state}",
        f"tmux_session: {result.tmux_session}",
        f"tui_session_id: {result.tui_session_id}",
        f"cwd: {result.cwd}",
        f"command: {' '.join(result.command)}",
    ]
    if result.running:
        lines.append(f"attach: tmux attach-session -t {result.tmux_session}")
    lines.extend(f"warning: {warning}" for warning in result.warnings)
    if result.stdout:
        lines.append(result.stdout.rstrip())
    if result.stderr:
        lines.append(result.stderr.rstrip())

    rendered: str = "\n".join(lines)
    return rendered


@daemon_app.command("status")
def daemon_status(
    cwd: Path = typer.Option(Path("."), "--cwd", help="Workspace root."),
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Durable TUI session id.",
    ),
    tmux_session: str | None = typer.Option(
        None,
        "--tmux-session",
        help="Optional tmux session name override.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Show the background comx-agent TUI daemon status.

    Args:
        cwd [Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        status: ComxTuiDaemonStatusResult = read_comx_tui_daemon_status(
            cwd,
            session_id,
            tmux_session=tmux_session,
        )
    except ValueError as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(status.model_dump_json(indent=2))
        return

    typer.echo(_format_status_human(status))


@daemon_app.command("start")
def daemon_start(
    cwd: Path = typer.Option(Path("."), "--cwd", help="Workspace root."),
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Durable TUI session id.",
    ),
    tmux_session: str | None = typer.Option(
        None,
        "--tmux-session",
        help="Optional tmux session name override.",
    ),
    executable: str = typer.Option(
        "comx-agent",
        "--executable",
        help="Executable used inside tmux.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Kill an existing tmux session before starting.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the tmux command without executing it.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Start the comx-agent TUI in a detached tmux session.

    Args:
        cwd [Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session override.
        executable [str]: Executable used inside tmux.
        force [bool]: Whether to kill an existing session first.
        dry_run [bool]: Whether to preview without execution.
        json_output [bool]: Whether to print JSON.
    """
    try:
        if dry_run:
            preview: ComxTuiDaemonCommandPreview = build_daemon_start_command(
                cwd,
                session_id,
                executable=executable,
                tmux_session=tmux_session,
            )
            if json_output:
                typer.echo(preview.model_dump_json(indent=2))
            else:
                typer.echo(" ".join(preview.command))
            return

        result: ComxTuiDaemonActionResult = start_comx_tui_daemon(
            cwd,
            session_id,
            executable=executable,
            tmux_session=tmux_session,
            force=force,
        )
    except ValueError as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
    else:
        typer.echo(_format_action_human(result))

    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@daemon_app.command("stop")
def daemon_stop(
    cwd: Path = typer.Option(Path("."), "--cwd", help="Workspace root."),
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Durable TUI session id.",
    ),
    tmux_session: str | None = typer.Option(
        None,
        "--tmux-session",
        help="Optional tmux session name override.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Stop the background comx-agent TUI daemon.

    Args:
        cwd [Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        result: ComxTuiDaemonActionResult = stop_comx_tui_daemon(
            cwd,
            session_id,
            tmux_session=tmux_session,
        )
    except ValueError as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
    else:
        typer.echo(_format_action_human(result))

    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)


@daemon_app.command("attach")
def daemon_attach(
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Durable TUI session id.",
    ),
    tmux_session: str | None = typer.Option(
        None,
        "--tmux-session",
        help="Optional tmux session name override.",
    ),
) -> None:
    """Attach the current terminal to the background TUI session.

    Args:
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session override.
    """
    try:
        exit_code: int = attach_comx_tui_daemon(
            session_id,
            tmux_session=tmux_session,
        )
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error

    raise typer.Exit(code=exit_code)
