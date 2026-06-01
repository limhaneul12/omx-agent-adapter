from enum import StrEnum


class McpServerSource(StrEnum):
    """Configuration sources that comx-agent can consume for MCP servers."""

    CODEX = "codex"
    REPO = "repo"


class McpTransportKind(StrEnum):
    """MCP transport kinds supported by the client surface."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
