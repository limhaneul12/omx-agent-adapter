from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.schemas.mcp.client_schemas import (
    McpServerConfig,
    McpServerSource,
    McpServerTransport,
    McpToolCallResult,
    McpToolDescriptor,
    McpToolListResult,
    McpTransportKind,
)


def _write_mcp_config(root: Path) -> None:
    (root / ".comx-agent.toml").write_text(
        """
[mcp.servers.local_state]
enabled = true
command = "omx"
args = ["mcp-serve", "state"]
""".strip(),
        encoding="utf-8",
    )


def _server() -> McpServerConfig:
    return McpServerConfig(
        name="local_state",
        source=McpServerSource.REPO,
        enabled=True,
        transport=McpServerTransport(
            type=McpTransportKind.STDIO,
            command="omx",
            args=("mcp-serve", "state"),
        ),
    )


def test_mcp_servers_cli_lists_repo_config_without_codex(tmp_path: Path) -> None:
    _write_mcp_config(tmp_path)

    result = CliRunner().invoke(
        app,
        ["mcp", "servers", "--cwd", str(tmp_path), "--no-codex", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["repo_count"] == 1
    assert payload["servers"][0]["qualified_name"] == "repo:local_state"
    assert payload["servers"][0]["transport"]["args"] == ["mcp-serve", "state"]


def test_mcp_tools_cli_uses_client_reader(monkeypatch, tmp_path: Path) -> None:
    _write_mcp_config(tmp_path)

    async def fake_list_mcp_tools(server: McpServerConfig) -> McpToolListResult:
        assert server.name == "local_state"
        return McpToolListResult(
            server=server,
            tools=(
                McpToolDescriptor(
                    server_name=server.name,
                    server_source=server.source,
                    name="state_read",
                    description="Read state.",
                    input_schema={"type": "object"},
                ),
            ),
        )

    monkeypatch.setattr(
        "omx_remote.cli_launcher.mcp_cli.list_mcp_tools",
        fake_list_mcp_tools,
    )

    result = CliRunner().invoke(
        app,
        ["mcp", "tools", "local_state", "--cwd", str(tmp_path), "--no-codex", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["tools"][0]["name"] == "state_read"
    assert payload["tools"][0]["input_schema"]["type"] == "object"


def test_mcp_call_cli_defaults_to_dry_run(tmp_path: Path) -> None:
    _write_mcp_config(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "mcp",
            "call",
            "local_state",
            "state_list_active",
            "--cwd",
            str(tmp_path),
            "--no-codex",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["execute_required"] is True
    assert "Dry-run only" in payload["warnings"][0]


def test_mcp_call_cli_executes_when_requested(monkeypatch, tmp_path: Path) -> None:
    _write_mcp_config(tmp_path)

    async def fake_call_mcp_tool(
        server: McpServerConfig,
        tool_name: str,
        arguments: dict[str, object],
    ) -> McpToolCallResult:
        assert server.name == "local_state"
        assert tool_name == "state_list_active"
        assert arguments == {"mode": "state"}
        return McpToolCallResult(
            server=server,
            tool_name=tool_name,
            arguments={"mode": "state"},
            executed=True,
            result={"content": [{"type": "text", "text": "{}"}]},
        )

    monkeypatch.setattr(
        "omx_remote.cli_launcher.mcp_cli.call_mcp_tool",
        fake_call_mcp_tool,
    )

    result = CliRunner().invoke(
        app,
        [
            "mcp",
            "call",
            "local_state",
            "state_list_active",
            "--cwd",
            str(tmp_path),
            "--no-codex",
            "--arguments-json",
            '{"mode":"state"}',
            "--execute",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["executed"] is True
    assert payload["result"]["content"][0]["type"] == "text"


def test_mcp_serve_cli_help_mentions_omx_agent_tools() -> None:
    result = CliRunner().invoke(app, ["mcp", "serve", "--help"])

    assert result.exit_code == 0
    assert "omx-agent" in result.stdout
    assert "--cwd" in result.stdout
