from pathlib import Path

import orjson

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.runtime.mcp.mcp_registry_reader import read_mcp_servers
from omx_remote.schemas.mcp_client_schemas import (
    McpServerConfig,
    McpServerListResult,
    McpServerRegistrationResult,
    McpServerRemovalResult,
    McpToolListResult,
    McpTransportKind,
)


def _arguments_json(value: str | None) -> JsonObject:
    """Parse CLI JSON arguments for an MCP tool call.

    Args:
        value [str | None]: Inline JSON object text.

    Returns:
        JsonObject: Parsed argument object.
    """
    if value is None:
        empty_arguments: JsonObject = {}
        return empty_arguments

    try:
        decoded: JsonValue = orjson.loads(value)
    except orjson.JSONDecodeError as error:
        raise ValueError(f"--arguments-json is not valid JSON: {error}") from error
    if not isinstance(decoded, dict):
        raise ValueError("--arguments-json must decode to a JSON object.")

    arguments: JsonObject = decoded
    return arguments


def _env_pairs(values: list[str] | None) -> dict[str, str]:
    """Parse repeated KEY=VALUE environment options.

    Args:
        values [list[str] | None]: Raw CLI option values.

    Returns:
        dict[str, str]: Parsed environment values.
    """
    if values is None:
        empty_env: dict[str, str] = {}
        return empty_env

    env: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--env values must use KEY=VALUE format.")
        key, env_value = value.split("=", 1)
        if not key:
            raise ValueError("--env values must include a non-empty KEY.")
        env[key] = env_value
    return env


def _registration_target_text(server: McpServerConfig) -> str:
    """Render the target for one registered MCP server.

    Args:
        server [McpServerConfig]: Registered server.

    Returns:
        str: Human-readable target.
    """
    if server.transport.type == McpTransportKind.STREAMABLE_HTTP:
        target: str = server.transport.url or "-"
        return target
    command_parts: tuple[str, ...] = ()
    if server.transport.command is not None:
        command_parts = (server.transport.command, *server.transport.args)
    target = " ".join(command_parts) if command_parts else "-"
    return target


def _format_registration_human(result: McpServerRegistrationResult) -> str:
    """Render one MCP registration result for humans.

    Args:
        result [McpServerRegistrationResult]: Registration result.

    Returns:
        str: Human-readable result.
    """
    action = "registered"
    if result.replaced_existing:
        action = "replaced"
    lines: list[str] = [
        f"{action}: {result.server.qualified_name}",
        f"target: {_registration_target_text(result.server)}",
        f"config: {result.config_path}",
    ]
    lines.extend(f"warning: {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _format_removal_human(result: McpServerRemovalResult) -> str:
    """Render one MCP removal result for humans.

    Args:
        result [McpServerRemovalResult]: Removal result.

    Returns:
        str: Human-readable result.
    """
    status = "removed" if result.removed else "not_found"
    lines: list[str] = [
        f"{status}: repo:{result.server_name}",
        f"config: {result.config_path}",
    ]
    lines.extend(f"warning: {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _read_registry(
    cwd: Path,
    config_path: Path | None,
    include_codex: bool,
) -> McpServerListResult:
    """Read the MCP registry for CLI commands.

    Args:
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        include_codex [bool]: Whether to include Codex registry data.

    Returns:
        McpServerListResult: Discovered registry.
    """
    registry: McpServerListResult = read_mcp_servers(
        cwd=cwd,
        config_path=config_path,
        include_codex=include_codex,
    )
    return registry


def _format_servers_human(result: McpServerListResult) -> str:
    """Render MCP servers for human terminal output.

    Args:
        result [McpServerListResult]: Server registry.

    Returns:
        str: Human-readable registry summary.
    """
    if not result.servers:
        server_text: str = "No MCP servers discovered."
        return server_text

    lines: list[str] = []
    for server in result.servers:
        target: str = server.transport.url or server.transport.command or "-"
        status: str = "enabled" if server.enabled else "disabled"
        lines.append(
            f"{server.qualified_name}\t{status}\t{server.transport.type}\t{target}"
        )
    lines.extend(f"warning: {warning}" for warning in result.warnings)

    server_text = "\n".join(lines)
    return server_text


def _format_tools_human(result: McpToolListResult) -> str:
    """Render MCP tools for human terminal output.

    Args:
        result [McpToolListResult]: Tool list.

    Returns:
        str: Human-readable tool summary.
    """
    if not result.tools:
        tool_text: str = f"No tools advertised by {result.server.qualified_name}."
        return tool_text

    lines: list[str] = []
    for tool in result.tools:
        description: str = "" if tool.description is None else tool.description
        lines.append(f"{tool.name}\t{description}")

    tool_text = "\n".join(lines)
    return tool_text


def _guard_disabled_server(server: McpServerConfig, allow_disabled: bool) -> None:
    """Reject disabled MCP servers unless the caller explicitly opts in.

    Args:
        server [McpServerConfig]: Resolved server.
        allow_disabled [bool]: Whether disabled servers may be contacted.
    """
    if server.enabled or allow_disabled:
        return

    reason: str = "no disabled_reason was provided"
    if server.disabled_reason is not None:
        reason = server.disabled_reason
    raise ValueError(
        f"MCP server {server.qualified_name} is disabled; pass --allow-disabled to inspect it. Reason: {reason}"
    )
