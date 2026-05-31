from enum import StrEnum
from typing import Literal, cast

type McpLogLevelValue = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class McpServerSource(StrEnum):
    """Configuration sources that comx-agent can consume for MCP servers."""

    CODEX = "codex"
    REPO = "repo"


class McpTransportKind(StrEnum):
    """MCP transport kinds supported by the client surface."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"


class McpLogLevel(StrEnum):
    """FastMCP log levels accepted by the adapter-owned MCP server."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def normalize_mcp_log_level(value: McpLogLevel | str) -> McpLogLevel:
    """Normalize one MCP log-level value.

    Args:
        value [McpLogLevel | str]: Raw log-level value from CLI or direct calls.

    Returns:
        McpLogLevel: Canonical log-level enum member.

    Raises:
        ValueError: Raised when the value is not an accepted log level.
    """
    try:
        normalized_value = McpLogLevel(value)
    except ValueError as error:
        allowed_values: str = ", ".join(level.value for level in McpLogLevel)
        raise ValueError(f"log level must be one of: {allowed_values}") from error
    return normalized_value


def mcp_log_level_value(value: McpLogLevel | str) -> McpLogLevelValue:
    """Normalize one MCP log-level value for FastMCP's literal-typed boundary.

    Args:
        value [McpLogLevel | str]: Raw log-level value from CLI or direct calls.

    Returns:
        McpLogLevelValue: Log-level text accepted by FastMCP.
    """
    normalized_value = normalize_mcp_log_level(value)
    # FastMCP annotates these strings as Literals; the enum already owns that set.
    log_level_text = cast(McpLogLevelValue, normalized_value.value)
    return log_level_text
