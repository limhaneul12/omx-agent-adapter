from pathlib import Path

import pytest

from omx_remote.runtime.mcp.codex_mcp_registry import servers_from_codex_payload
from omx_remote.runtime.mcp.mcp_config_loader import load_repo_mcp_servers
from omx_remote.runtime.mcp.mcp_registry_reader import (
    McpServerResolutionError,
    read_mcp_servers,
    resolve_mcp_server,
)
from omx_remote.schemas.mcp.client_schemas import McpServerSource, McpTransportKind


def test_repo_mcp_config_reads_comx_agent_toml(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[mcp.servers.local_state]
enabled = true
command = "omx"
args = ["mcp-serve", "state"]
env = { OMX_TEST = "1" }
env_vars = ["OMX_TOKEN"]
""".strip(),
        encoding="utf-8",
    )

    servers = load_repo_mcp_servers(cwd=tmp_path)

    assert len(servers) == 1
    assert servers[0].qualified_name == "repo:local_state"
    assert servers[0].transport.type == McpTransportKind.STDIO
    assert servers[0].transport.command == "omx"
    assert servers[0].transport.args == ("mcp-serve", "state")
    assert servers[0].transport.env[0].name == "OMX_TEST"
    assert servers[0].transport.env_vars == ("OMX_TOKEN",)


def test_repo_mcp_config_reads_codex_style_section(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[mcp_servers.search]
enabled = false
url = "https://mcp.example.test/mcp"
""".strip(),
        encoding="utf-8",
    )

    servers = load_repo_mcp_servers(cwd=tmp_path)

    assert servers[0].qualified_name == "repo:search"
    assert servers[0].enabled is False
    assert servers[0].transport.type == McpTransportKind.STREAMABLE_HTTP
    assert servers[0].transport.url == "https://mcp.example.test/mcp"


def test_codex_mcp_payload_normalizes_stdio_server() -> None:
    servers = servers_from_codex_payload(
        [
            {
                "name": "omx_state",
                "enabled": False,
                "transport": {
                    "type": "stdio",
                    "command": "omx",
                    "args": ["mcp-serve", "state"],
                    "env": None,
                    "env_vars": [],
                    "cwd": None,
                },
                "startup_timeout_sec": None,
                "tool_timeout_sec": None,
                "auth_status": "unsupported",
                "disabled_reason": None,
            }
        ]
    )

    assert servers[0].source == McpServerSource.CODEX
    assert servers[0].name == "omx_state"
    assert servers[0].transport.command == "omx"
    assert servers[0].transport.args == ("mcp-serve", "state")
    assert servers[0].auth_status == "unsupported"


def test_mcp_registry_prefers_unambiguous_repo_server(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[mcp.servers.omx_state]
command = "omx"
args = ["mcp-serve", "state"]
""".strip(),
        encoding="utf-8",
    )
    codex_servers = servers_from_codex_payload(
        [
            {
                "name": "codex_only",
                "enabled": True,
                "transport": {
                    "type": "stdio",
                    "command": "omx",
                    "args": ["mcp-serve", "wiki"],
                    "env": None,
                    "env_vars": [],
                    "cwd": None,
                },
            }
        ]
    )
    monkeypatch.setattr(
        "omx_remote.runtime.mcp.mcp_registry_reader.read_codex_mcp_servers",
        lambda: codex_servers,
    )

    registry = read_mcp_servers(cwd=tmp_path)

    assert registry.codex_count == 1
    assert registry.repo_count == 1
    assert resolve_mcp_server(registry.servers, "omx_state").source == McpServerSource.REPO
    assert resolve_mcp_server(registry.servers, "codex:codex_only").source == McpServerSource.CODEX


def test_mcp_registry_reports_ambiguous_short_names(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[mcp.servers.shared]
command = "omx"
args = ["mcp-serve", "state"]
""".strip(),
        encoding="utf-8",
    )
    codex_servers = servers_from_codex_payload(
        [
            {
                "name": "shared",
                "enabled": True,
                "transport": {
                    "type": "stdio",
                    "command": "omx",
                    "args": ["mcp-serve", "state"],
                    "env": None,
                    "env_vars": [],
                    "cwd": None,
                },
            }
        ]
    )
    monkeypatch.setattr(
        "omx_remote.runtime.mcp.mcp_registry_reader.read_codex_mcp_servers",
        lambda: codex_servers,
    )

    registry = read_mcp_servers(cwd=tmp_path)

    with pytest.raises(McpServerResolutionError, match="ambiguous"):
        resolve_mcp_server(registry.servers, "shared")
