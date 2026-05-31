import asyncio
from pathlib import Path

from omx_remote.runtime.mcp.mcp_registry_reader import (
    read_mcp_servers,
    resolve_mcp_server,
)
from omx_remote.runtime.mcp.mcp_tool_client import list_mcp_tools
from omx_remote.schemas.comx.tui_schemas import ComxTuiCommandResult
from omx_remote.schemas.mcp.client_schemas import (
    McpServerConfig,
    McpServerListResult,
    McpToolListResult,
    McpTransportKind,
)

SECRET_ARGUMENT_TERMS: tuple[str, ...] = (
    "auth",
    "bearer",
    "credential",
    "header",
    "key",
    "password",
    "secret",
    "token",
)
SECRET_ARGUMENT_FLAGS: frozenset[str] = frozenset(
    {
        "-H",
        "--header",
        "--headers",
        "--authorization",
    }
)


def _strip_url_query(value: str) -> str:
    """Remove query strings from URL-like display values.

    Args:
        value [str]: Candidate display value.

    Returns:
        str: Value with URL query removed.
    """
    if "://" not in value or "?" not in value:
        return value
    redacted_value: str = value.split("?", 1)[0]
    return redacted_value


def _secret_argument_name(value: str) -> bool:
    """Check whether a CLI argument name appears secret-bearing.

    Args:
        value [str]: Argument name or key.

    Returns:
        bool: True when the name is secret-like.
    """
    normalized_value: str = value.strip().lstrip("-").lower().replace("_", "-")
    secret_like: bool = value in SECRET_ARGUMENT_FLAGS or any(
        term in normalized_value for term in SECRET_ARGUMENT_TERMS
    )
    return secret_like


def _redact_argument_value(value: str) -> str:
    """Redact secret-looking CLI argument values while preserving shape.

    Args:
        value [str]: CLI argument value.

    Returns:
        str: Redacted display value.
    """
    if "=" in value:
        key, _ = value.split("=", 1)
        if _secret_argument_name(key):
            return f"{key}=<redacted>"
    if ":" in value:
        key, _ = value.split(":", 1)
        if _secret_argument_name(key):
            return f"{key}:<redacted>"
    redacted_value: str = _strip_url_query(value)
    return redacted_value


def _redacted_stdio_target(command: str, args: tuple[str, ...]) -> str:
    """Render a stdio MCP target without leaking secret-like args.

    Args:
        command [str]: Stdio command.
        args [tuple[str, ...]]: Stdio command args.

    Returns:
        str: Safe target display string.
    """
    rendered_parts: list[str] = [command]
    redact_next = False
    for arg in args:
        if redact_next:
            rendered_parts.append("<redacted>")
            redact_next = False
            continue
        rendered_arg: str = _redact_argument_value(arg)
        rendered_parts.append(rendered_arg)
        if rendered_arg == arg and _secret_argument_name(arg):
            redact_next = True

    rendered_target: str = " ".join(rendered_parts)
    return rendered_target


def _redacted_target(server: McpServerConfig) -> str:
    """Render a safe MCP target string.

    Args:
        server [McpServerConfig]: MCP server.

    Returns:
        str: Redacted target string.
    """
    if server.transport.type == McpTransportKind.STREAMABLE_HTTP:
        if server.transport.url is None:
            return "-"
        url_without_query: str = _strip_url_query(server.transport.url)
        return url_without_query

    if server.transport.command is not None:
        return _redacted_stdio_target(
            server.transport.command,
            server.transport.args,
        )
    return "-"


def _format_mcp_server_rows(registry: McpServerListResult) -> str:
    """Render MCP server rows for a TUI command result.

    Args:
        registry [McpServerListResult]: MCP registry.

    Returns:
        str: Human-readable rows.
    """
    if not registry.servers:
        return (
            "No MCP servers discovered. Use `comx-agent mcp add ...` to register one."
        )

    lines: list[str] = [
        "source  name                         enabled  auth          transport          target",
    ]
    for server in registry.servers:
        enabled_label: str = "yes" if server.enabled else "no"
        auth_label: str = server.auth_status or "n/a"
        lines.append(
            f"{server.source:<6}  {server.qualified_name:<27}  "
            f"{enabled_label:<7}  {auth_label:<12}  {server.transport.type:<17}  "
            f"{_redacted_target(server)}"
        )
        if server.disabled_reason is not None:
            lines.append(f"  disabled_reason: {server.disabled_reason}")
    lines.extend(f"warning: {warning}" for warning in registry.warnings)
    rendered_rows: str = "\n".join(lines)
    return rendered_rows


def _format_tool_rows(result: McpToolListResult) -> str:
    """Render MCP tool rows.

    Args:
        result [McpToolListResult]: Tool list result.

    Returns:
        str: Human-readable rows.
    """
    if not result.tools:
        return f"No tools advertised by {result.server.qualified_name}."

    lines: list[str] = [f"tools for {result.server.qualified_name}:"]
    for tool in result.tools:
        description: str = tool.description or tool.title or "-"
        lines.append(f"- {tool.name}: {description}")
    lines.extend(f"warning: {warning}" for warning in result.warnings)
    rendered_rows: str = "\n".join(lines)
    return rendered_rows


def build_tui_mcp_result(cwd: Path, args: str) -> ComxTuiCommandResult:
    """Build an MCP command result.

    Args:
        cwd [Path]: Workspace root.
        args [str]: Inline args after /mcp.

    Returns:
        ComxTuiCommandResult: Result.
    """
    normalized_args: str = args.strip()
    if normalized_args.startswith("tools "):
        server_name: str = normalized_args.removeprefix("tools ").strip()
        if not server_name:
            raise ValueError("/mcp tools requires a server name.")
        registry: McpServerListResult = read_mcp_servers(cwd=cwd)
        server: McpServerConfig = resolve_mcp_server(registry.servers, server_name)
        try:
            tool_result: McpToolListResult = asyncio.run(list_mcp_tools(server))
        except Exception as error:
            result = ComxTuiCommandResult(
                command="/mcp tools",
                title=f"MCP tools error: {server.qualified_name}",
                body=f"Could not list tools for {server.qualified_name}: {error}",
                warnings=(
                    "MCP tool listing may start an external stdio process or open a network connection.",
                    *registry.warnings,
                ),
            )
            return result
        result = ComxTuiCommandResult(
            command="/mcp tools",
            title=f"MCP tools: {server.qualified_name}",
            body=_format_tool_rows(tool_result),
            warnings=(*registry.warnings, *tool_result.warnings),
        )
        return result

    if normalized_args.startswith("call "):
        call_parts: list[str] = normalized_args.removeprefix("call ").split()
        if len(call_parts) < 2:
            raise ValueError("/mcp call requires <server> <tool>.")
        registry = read_mcp_servers(cwd=cwd)
        server = resolve_mcp_server(registry.servers, call_parts[0])
        body = "\n".join(
            (
                f"dry_run: {server.qualified_name}.{call_parts[1]} not executed",
                "Use `comx-agent mcp call ... --execute` outside the TUI for explicit execution.",
            )
        )
        result = ComxTuiCommandResult(
            command="/mcp call",
            title="MCP tool call preview",
            body=body,
            warnings=("Dry-run only. No MCP tool was executed.", *registry.warnings),
        )
        return result

    registry = read_mcp_servers(cwd=cwd)
    title: str = "MCP servers"
    if normalized_args == "verbose":
        title = "MCP servers (verbose, redacted)"
    result = ComxTuiCommandResult(
        command="/mcp",
        title=title,
        body=_format_mcp_server_rows(registry),
        warnings=registry.warnings,
    )
    return result
