import orjson
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.cli_launcher import comx_cli
from omx_remote.cli_launcher.comx_cli import ComxSlashCompleter
from omx_remote.runtime.comx.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.runtime.comx.tui_interaction import format_tui_slash_command_help
from omx_remote.runtime.comx.tui_renderer import build_tui_snapshot, render_tui_frame
from omx_remote.runtime.comx.tui_session_store import (
    read_tui_session,
    start_or_resume_tui_session,
)
from omx_remote.schemas.next.next_action_schemas import NextActionResult


def test_comx_surface_inventory_distinguishes_native_and_composed(tmp_path) -> None:
    inventory = build_comx_control_surface_inventory(cwd=tmp_path)

    native_names = {command.name for command in inventory.native_commands}
    composed_ids = {command.qualified_id for command in inventory.composed_commands}

    assert "mcp" in native_names
    assert "tui" in native_names
    assert "sessions" in native_names
    assert "daemon" in native_names
    assert "surface" in native_names
    assert "builtin:review-diff" in composed_ids
    assert "builtin:mcp-registry-inspect" in composed_ids


def test_surface_cli_outputs_json(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        ["surface", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["product_name"] == "comx-agent"
    assert "agent-remote" in payload["compatibility_aliases"]
    assert any(command["name"] == "mcp" for command in payload["native_commands"])
    assert any(
        command["qualified_id"] == "builtin:review-diff"
        for command in payload["composed_commands"]
    )


def test_tui_renderer_includes_screenshot_style_labels(tmp_path) -> None:
    snapshot = build_tui_snapshot(cwd=tmp_path, prompt="Run /review")
    frame = render_tui_frame(snapshot)

    assert "COMX Agent" in frame
    assert "workspace:" in frame
    assert "> Run /review" in frame
    assert "MCP client" in frame


def test_tui_help_mentions_slash_completion_and_free_text() -> None:
    help_text = format_tui_slash_command_help()

    assert "type '/'" in help_text
    assert "enter free text as a prompt" in help_text
    assert "/mcp servers" in help_text


def test_tui_slash_completer_suggests_nested_commands() -> None:
    completer = ComxSlashCompleter()

    completions = list(
        completer.get_completions(Document("/m"), CompleteEvent(completion_requested=True))
    )

    assert any(completion.text == "/mcp servers" for completion in completions)


def test_tui_loop_treats_non_slash_input_as_prompt(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    next_action = NextActionResult(
        recommended_action="observe",
        safe_to_mutate=True,
        requires_review=False,
        summary="No blocking evidence was found.",
        why=("Cockpit found no active runtime.",),
        source_names=("runtime_status",),
    )
    session = start_or_resume_tui_session(tmp_path, "alpha", "Run /help")

    class FakePromptSession:
        """Deterministic prompt session for testing the TUI loop."""

        def __init__(self) -> None:
            self._inputs = iter(("안녕?", "/quit"))

        def prompt(self, *args, **kwargs) -> str:
            return next(self._inputs)

    monkeypatch.setattr(
        comx_cli,
        "_build_prompt_session",
        lambda cwd, session_id: FakePromptSession(),
    )

    final_session = comx_cli._run_tui_loop(
        tmp_path,
        next_action,
        session,
        "FRAME",
    )
    output = capsys.readouterr().out

    assert final_session.status == "closed"
    assert "prompt captured: 안녕?" in output
    assert "unknown command" not in output


def test_tui_once_persists_session_record(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "tui",
            "--cwd",
            str(tmp_path),
            "--once",
            "--session-id",
            "alpha",
            "--prompt",
            "Run /review",
        ],
    )

    assert result.exit_code == 0
    session = read_tui_session(tmp_path, "alpha")
    assert session is not None
    assert session.session_id == "alpha"
    assert session.status == "closed"
    assert session.last_prompt == "Run /review"
    assert session.render_count == 1
    assert session.events[-1].kind == "closed"


def test_tui_resume_uses_last_prompt_when_prompt_omitted(tmp_path) -> None:
    first_result = CliRunner().invoke(
        app,
        [
            "tui",
            "--cwd",
            str(tmp_path),
            "--once",
            "--session-id",
            "alpha",
            "--prompt",
            "Remember me",
        ],
    )
    assert first_result.exit_code == 0

    second_result = CliRunner().invoke(
        app,
        ["tui", "--cwd", str(tmp_path), "--once", "--session-id", "alpha"],
    )

    assert second_result.exit_code == 0
    assert "> Remember me" in second_result.stdout
    session = read_tui_session(tmp_path, "alpha")
    assert session is not None
    assert session.last_prompt == "Remember me"
    assert session.render_count == 2


def test_sessions_cli_lists_and_shows_saved_session(tmp_path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "tui",
            "--cwd",
            str(tmp_path),
            "--once",
            "--session-id",
            "alpha",
            "--prompt",
            "Run /review",
        ],
    )
    assert result.exit_code == 0

    list_result = CliRunner().invoke(
        app,
        ["sessions", "list", "--cwd", str(tmp_path), "--json"],
    )
    assert list_result.exit_code == 0
    list_payload = orjson.loads(list_result.stdout)
    assert list_payload["sessions"][0]["session_id"] == "alpha"

    show_result = CliRunner().invoke(
        app,
        ["sessions", "show", "alpha", "--cwd", str(tmp_path), "--json"],
    )
    assert show_result.exit_code == 0
    show_payload = orjson.loads(show_result.stdout)
    assert show_payload["last_prompt"] == "Run /review"
