from pathlib import Path

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


def test_tui_loop_routes_session_command_through_typed_result(
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
        """Deterministic prompt session for testing /session routing."""

        def __init__(self) -> None:
            self._inputs = iter(("/session", "/quit"))

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
    assert "## session" in output
    assert "session=alpha" in output


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


def test_tui_catalog_promotes_codex_omx_commands() -> None:
    from omx_remote.runtime.comx.tui_command_catalog import (
        find_tui_slash_command,
        get_tui_slash_command_args,
        list_tui_slash_commands,
    )

    commands = list_tui_slash_commands()
    names = [command.name for command in commands]

    assert names.index("/status") < names.index("/mcp")
    assert "/research" in names
    assert "/team" in names
    assert "/ultragoal" in names
    assert find_tui_slash_command("/mcp tools repo:local_state") is not None
    assert get_tui_slash_command_args("/research codex mcp UX") == "codex mcp UX"


def test_tui_snapshot_includes_command_and_mcp_counts(monkeypatch, tmp_path) -> None:
    from omx_remote.schemas.mcp.client_schemas import McpServerListResult

    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_renderer.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(),
            codex_count=0,
            repo_count=0,
            enabled_count=0,
        ),
    )

    snapshot = build_tui_snapshot(cwd=tmp_path, prompt="Run /status")
    frame = render_tui_frame(snapshot)

    assert snapshot.slash_command_count >= 10
    assert snapshot.mcp_server_count == 0
    assert snapshot.composed_command_count >= 1
    assert "commands" in frame
    assert "/status" in snapshot.tips[0]


def test_tui_router_lists_mcp_servers_with_redacted_targets(monkeypatch, tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
    from omx_remote.schemas.mcp.client_schemas import (
        McpServerConfig,
        McpServerListResult,
        McpServerSource,
        McpServerTransport,
        McpTransportKind,
    )

    server = McpServerConfig(
        name="search",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STREAMABLE_HTTP,
            url="https://mcp.example.test/rpc?token=secret",
            bearer_token_env_var="SEARCH_TOKEN",
        ),
        auth_status="bearer_token",
    )
    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(server,),
            codex_count=0,
            repo_count=1,
            enabled_count=1,
        ),
    )

    result = route_tui_slash_command("/mcp", cwd=tmp_path)

    assert result.title == "MCP servers"
    assert "repo:search" in result.body
    assert "https://mcp.example.test/rpc" in result.body
    assert "token=secret" not in result.body


def test_tui_router_redacts_stdio_secret_like_args(monkeypatch, tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
    from omx_remote.schemas.mcp.client_schemas import (
        McpServerConfig,
        McpServerListResult,
        McpServerSource,
        McpServerTransport,
        McpTransportKind,
    )

    server = McpServerConfig(
        name="secret_stdio",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STDIO,
            command="mcp-secret",
            args=(
                "--api-key",
                "plain-secret-value",
                "--token=inline-secret-value",
                "--header",
                "Authorization: Bearer hidden",
                "https://example.test/rpc?token=query-secret",
            ),
        ),
    )
    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(server,),
            codex_count=0,
            repo_count=1,
            enabled_count=1,
        ),
    )

    result = route_tui_slash_command("/mcp", cwd=tmp_path)

    assert "plain-secret-value" not in result.body
    assert "inline-secret-value" not in result.body
    assert "Bearer hidden" not in result.body
    assert "query-secret" not in result.body
    assert "--api-key <redacted>" in result.body
    assert "--token=<redacted>" in result.body


def test_tui_router_lists_mcp_tools(monkeypatch, tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
    from omx_remote.schemas.mcp.client_schemas import (
        McpServerConfig,
        McpServerListResult,
        McpServerSource,
        McpServerTransport,
        McpToolDescriptor,
        McpToolListResult,
        McpTransportKind,
    )

    server = McpServerConfig(
        name="local_state",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STDIO,
            command="omx",
            args=("mcp-serve", "state"),
        ),
    )
    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(server,),
            codex_count=0,
            repo_count=1,
            enabled_count=1,
        ),
    )

    async def fake_list_mcp_tools(server_config: McpServerConfig) -> McpToolListResult:
        assert server_config.name == "local_state"
        return McpToolListResult(
            server=server_config,
            tools=(
                McpToolDescriptor(
                    server_name=server_config.name,
                    server_source=server_config.source,
                    name="state_read",
                    description="Read active state.",
                ),
            ),
        )

    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.list_mcp_tools",
        fake_list_mcp_tools,
    )

    result = route_tui_slash_command("/mcp tools local_state", cwd=tmp_path)

    assert result.command == "/mcp tools"
    assert "state_read" in result.body
    assert "Read active state" in result.body


def test_tui_router_surfaces_mcp_tool_listing_errors(monkeypatch, tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
    from omx_remote.schemas.mcp.client_schemas import (
        McpServerConfig,
        McpServerListResult,
        McpServerSource,
        McpServerTransport,
        McpTransportKind,
    )

    server = McpServerConfig(
        name="missing",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STDIO,
            command="missing-mcp-binary",
        ),
    )
    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(server,),
            codex_count=0,
            repo_count=1,
            enabled_count=1,
        ),
    )

    async def fake_list_mcp_tools(server_config: McpServerConfig) -> None:
        raise FileNotFoundError(server_config.transport.command or "missing")

    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.list_mcp_tools",
        fake_list_mcp_tools,
    )

    result = route_tui_slash_command("/mcp tools missing", cwd=tmp_path)

    assert result.command == "/mcp tools"
    assert result.title == "MCP tools error: repo:missing"
    assert "Could not list tools" in result.body
    assert "external stdio process" in result.warnings[0]


def test_tui_router_surfaces_mcp_http_exception_group(monkeypatch, tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command
    from omx_remote.schemas.mcp.client_schemas import (
        McpServerConfig,
        McpServerListResult,
        McpServerSource,
        McpServerTransport,
        McpTransportKind,
    )

    server = McpServerConfig(
        name="http_down",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STREAMABLE_HTTP,
            url="http://127.0.0.1:1/mcp",
        ),
    )
    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.read_mcp_servers",
        lambda cwd: McpServerListResult(
            servers=(server,),
            codex_count=0,
            repo_count=1,
            enabled_count=1,
        ),
    )

    async def fake_list_mcp_tools(server_config: McpServerConfig) -> None:
        raise ExceptionGroup(
            "unhandled errors in a TaskGroup",
            [ConnectionError(server_config.transport.url or "missing")],
        )

    monkeypatch.setattr(
        "omx_remote.runtime.comx.tui_command_router.list_mcp_tools",
        fake_list_mcp_tools,
    )

    result = route_tui_slash_command("/mcp tools http_down", cwd=tmp_path)

    assert result.command == "/mcp tools"
    assert result.title == "MCP tools error: repo:http_down"
    assert "unhandled errors in a TaskGroup" in result.body


def test_tui_router_handles_session_command(tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command

    result = route_tui_slash_command("/session", cwd=tmp_path)

    assert result.command == "/session"
    assert result.title == "session"
    assert "sessions show" in result.body


def test_research_command_writes_plan_artifact(tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command

    result = route_tui_slash_command(
        "/research compare Codex and OMX MCP ergonomics",
        cwd=tmp_path,
    )

    assert result.command == "/research"
    assert result.read_only is False
    assert result.artifact_path is not None
    payload = orjson.loads(Path(result.artifact_path).read_bytes())
    assert payload["objective"] == "compare Codex and OMX MCP ergonomics"
    assert "mcp" in payload["sources"]
    assert "no external research tools" in result.warnings[0]


def test_research_command_does_not_overwrite_same_objective(tmp_path) -> None:
    from omx_remote.runtime.comx.tui_command_router import route_tui_slash_command

    first = route_tui_slash_command("/research duplicate objective", cwd=tmp_path)
    second = route_tui_slash_command("/research duplicate objective", cwd=tmp_path)

    assert first.artifact_path is not None
    assert second.artifact_path is not None
    assert first.artifact_path != second.artifact_path
    assert Path(first.artifact_path).exists()
    assert Path(second.artifact_path).exists()
