import asyncio
from collections.abc import Iterable
from pathlib import Path

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.styles import Style
from pydantic import ValidationError

from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.runtime.comx.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
from omx_remote.runtime.comx.tui_interaction import (
    format_tui_slash_command_help,
    is_known_tui_slash_command,
    list_tui_slash_completion_items,
    normalize_tui_command_text,
)
from omx_remote.runtime.comx.tui_renderer import build_tui_snapshot, render_tui_frame
from omx_remote.runtime.comx.tui_session_store import (
    close_tui_session,
    list_tui_sessions,
    read_tui_session,
    record_tui_command,
    record_tui_render,
    resolve_session_root,
    start_or_resume_tui_session,
)
from omx_remote.runtime.next.next_action_reader import read_next_action
from omx_remote.schemas.comx.control_surface_schemas import ComxControlSurfaceInventory
from omx_remote.schemas.comx.session_schemas import (
    ComxTuiSessionListResult,
    ComxTuiSessionRecord,
)
from omx_remote.schemas.comx.tui_schemas import ComxTuiCommandResult
from omx_remote.schemas.next.next_action_schemas import (
    NextActionRequest,
    NextActionResult,
)

sessions_app = typer.Typer(
    help="Inspect durable comx-agent TUI sessions.",
    add_completion=False,
)


class ComxSlashCompleter(Completer):
    """Prompt-toolkit completer for comx-agent slash commands."""

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        """Yield slash-command completions.

        Args:
            document [Document]: Current prompt document.
            complete_event [CompleteEvent]: Completion trigger context.

        Returns:
            Iterable[Completion]: Completion candidates.
        """
        text_before_cursor: str = document.text_before_cursor
        if not text_before_cursor.startswith("/"):
            return

        for command_name, description in list_tui_slash_completion_items():
            if command_name.startswith(text_before_cursor):
                yield Completion(
                    command_name,
                    start_position=-len(text_before_cursor),
                    display_meta=description,
                )


def _format_surface_human(inventory: ComxControlSurfaceInventory) -> str:
    """Render comx-agent surface inventory for humans.

    Args:
        inventory [ComxControlSurfaceInventory]: Typed inventory.

    Returns:
        str: Human-readable summary.
    """
    lines: list[str] = [
        f"product: {inventory.product_name}",
        f"compatibility_aliases: {', '.join(inventory.compatibility_aliases)}",
        "native_commands:",
    ]
    lines.extend(
        f"- {command.name}: {command.description}"
        for command in inventory.native_commands
    )
    lines.append("composed_commands:")
    lines.extend(
        f"- {command.qualified_id}: {command.description}"
        for command in inventory.composed_commands
    )
    rendered: str = "\n".join(lines)
    return rendered


def _interactive_help_text() -> str:
    """Build the TUI slash-command help text.

    Returns:
        str: Help text.
    """
    help_text: str = format_tui_slash_command_help()
    return help_text


def _build_prompt_session(cwd: Path, session_id: str) -> PromptSession[str]:
    """Build a prompt-toolkit session with slash completions and durable history.

    Args:
        cwd [Path]: Workspace root.
        session_id [str]: Durable TUI session id.

    Returns:
        PromptSession[str]: Configured prompt session.
    """
    session_root: Path = resolve_session_root(cwd)
    session_root.mkdir(parents=True, exist_ok=True)
    history_path: Path = session_root / f"{session_id}.history"
    style = Style.from_dict(
        {
            "prompt": "ansicyan bold",
            "completion-menu.completion": "bg:#303342 #ffffff",
            "completion-menu.completion.current": "bg:#5f87ff #ffffff",
            "completion-menu.meta": "bg:#303342 #d0d0d0",
            "completion-menu.meta.current": "bg:#5f87ff #ffffff",
        }
    )
    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        completer=ComxSlashCompleter(),
        complete_while_typing=True,
        auto_suggest=AutoSuggestFromHistory(),
        style=style,
    )
    return prompt_session


def _run_tui_loop(
    cwd: Path,
    next_action: NextActionResult,
    session: ComxTuiSessionRecord,
    frame_text: str,
) -> ComxTuiSessionRecord:
    """Run the interactive TUI command loop.

    Args:
        cwd [Path]: Workspace root.
        next_action [NextActionResult]: Current next-action snapshot.
        session [ComxTuiSessionRecord]: Active persisted session.
        frame_text [str]: Current rendered frame for redraw.

    Returns:
        ComxTuiSessionRecord: Final persisted session record.
    """
    typer.echo("")
    typer.echo("Type '/' for completions, /help for commands, /quit to exit.")
    current_session: ComxTuiSessionRecord = session
    prompt_session: PromptSession[str] = _build_prompt_session(
        cwd,
        session.session_id,
    )
    while True:
        try:
            command_text: str = prompt_session.prompt(
                "> ",
                complete_while_typing=True,
            )
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            closed_session = close_tui_session(cwd, current_session, "terminal interrupt")
            return closed_session

        normalized_command: str = normalize_tui_command_text(command_text)
        if normalized_command == "":
            continue

        current_session = record_tui_command(cwd, current_session, normalized_command)
        if normalized_command in {"/quit", "/exit"}:
            closed_session = close_tui_session(cwd, current_session, "user quit")
            return closed_session
        if normalized_command == "/clear":
            clear()
            typer.echo(frame_text)
            continue
        if normalized_command.startswith("/"):
            if not is_known_tui_slash_command(normalized_command):
                typer.echo(f"unknown slash command: {normalized_command}")
                typer.echo("Type '/' to open completions or /help to list commands.")
                continue
            try:
                command_result: ComxTuiCommandResult = route_tui_slash_command(
                    normalized_command,
                    cwd=cwd,
                    next_action=next_action,
                    current_session=current_session,
                )
            except ValueError as error:
                typer.echo(str(error))
                continue
            typer.echo(f"## {command_result.title}")
            typer.echo(command_result.body)
            for warning in command_result.warnings:
                typer.echo(f"warning: {warning}")
            continue

        typer.echo(f"prompt captured: {normalized_command}")
        typer.echo(f"recommended next action: {next_action.summary}")
        typer.echo(
            "This TUI captured the prompt in the session. "
            "Use /next, /status, /mcp, /surface, or /research for execution routing."
        )


def surface_command(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve command recipes.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command config path override.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Show what comx-agent supports natively versus via composed recipes.

    Args:
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        inventory: ComxControlSurfaceInventory = build_comx_control_surface_inventory(
            cwd=cwd,
            config_path=config_path,
        )
    except (ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(inventory.model_dump_json(indent=2))
        return

    typer.echo(_format_surface_human(inventory))


def tui_command(
    cwd: Path = typer.Option(Path("."), "--cwd", help="Workspace root to inspect."),
    prompt: str | None = typer.Option(
        None,
        "--prompt",
        help="Optional prompt text to display in the input row.",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help="Render one frame and exit instead of opening the interactive loop.",
    ),
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Durable TUI session id stored under .comx-agent/sessions.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print frame data as JSON."),
) -> None:
    """Open a Codex-like comx-agent terminal console with slash completions.

    Args:
        cwd [Path]: Workspace root.
        prompt [str | None]: Optional prompt text for display.
        once [bool]: Whether to render once and exit.
        session_id [str]: Durable session id.
        json_output [bool]: Whether to print JSON frame data.
    """
    existing_session: ComxTuiSessionRecord | None = read_tui_session(cwd, session_id)
    prompt_text: str = prompt or (
        existing_session.last_prompt
        if existing_session is not None
        else "Run /help for commands"
    )
    session: ComxTuiSessionRecord = start_or_resume_tui_session(
        cwd,
        session_id,
        prompt_text,
    )
    request = NextActionRequest(repo_root=str(cwd.resolve()))
    next_action: NextActionResult = asyncio.run(read_next_action(request))
    snapshot = build_tui_snapshot(cwd=cwd, next_action=next_action, prompt=prompt_text)
    session = record_tui_render(cwd, session, snapshot.prompt)

    if json_output:
        typer.echo(snapshot.model_dump_json(indent=2))
        close_tui_session(cwd, session, "json render exited")
        return

    frame_text: str = render_tui_frame(snapshot)
    typer.echo(frame_text)
    if once:
        close_tui_session(cwd, session, "one-shot render exited")
        return

    final_session: ComxTuiSessionRecord = _run_tui_loop(
        cwd,
        next_action,
        session,
        frame_text,
    )
    typer.echo(f"session saved: {final_session.session_id}")


@sessions_app.command("list")
def sessions_list(
    cwd: Path = typer.Option(Path("."), "--cwd", help="Workspace root to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """List durable comx-agent TUI sessions.

    Args:
        cwd [Path]: Workspace root.
        json_output [bool]: Whether to print JSON.
    """
    result: ComxTuiSessionListResult = list_tui_sessions(cwd)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    if not result.sessions:
        typer.echo("No comx-agent TUI sessions found.")
        return

    for session in result.sessions:
        typer.echo(
            f"{session.session_id}\t{session.status}\t{session.updated_at}\t"
            f"{session.last_prompt}"
        )


@sessions_app.command("show")
def sessions_show(
    session_id: str = typer.Argument(..., help="Session id to inspect."),
    cwd: Path = typer.Option(Path("."), "--cwd", help="Workspace root to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Show one durable comx-agent TUI session.

    Args:
        session_id [str]: Session id.
        cwd [Path]: Workspace root.
        json_output [bool]: Whether to print JSON.
    """
    session: ComxTuiSessionRecord | None = read_tui_session(cwd, session_id)
    if session is None:
        if json_output:
            typer.echo(
                _format_error_payload(ValueError(f"No session named {session_id}."))
            )
        else:
            typer.echo(f"No session named {session_id}.")
        raise typer.Exit(code=2)

    if json_output:
        typer.echo(session.model_dump_json(indent=2))
        return

    typer.echo(f"session_id: {session.session_id}")
    typer.echo(f"status: {session.status}")
    typer.echo(f"updated_at: {session.updated_at}")
    typer.echo(f"last_prompt: {session.last_prompt}")
    typer.echo(f"commands: {len(session.command_history)}")
