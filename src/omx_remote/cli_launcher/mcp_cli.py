import asyncio
from pathlib import Path
from typing import Literal, cast

import orjson
import typer
from pydantic import ValidationError

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.runtime.mcp.mcp_registry_reader import (
    McpServerResolutionError,
    read_mcp_servers,
    resolve_mcp_server,
)
from omx_remote.runtime.mcp.mcp_server_registration import (
    McpConfigWriteError,
    import_codex_mcp_server,
    register_repo_mcp_server,
    remove_repo_mcp_server,
)
from omx_remote.runtime.mcp.mcp_tool_client import (
    McpToolClientError,
    call_mcp_tool,
    list_mcp_tools,
)
from omx_remote.runtime.mcp.omx_agent_mcp_server import run_omx_agent_mcp_stdio
from omx_remote.schemas.mcp.client_schemas import (
    McpServerConfig,
    McpServerListResult,
    McpServerRegistrationResult,
    McpServerRemovalResult,
    McpToolCallPlan,
    McpToolCallResult,
    McpToolListResult,
    McpTransportKind,
    RepoMcpServerDefinition,
)

type McpServeLogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

mcp_app = typer.Typer(
    help="Consume external MCP servers/tools like Codex, or serve omx-agent tools.",
    add_completion=False,
)


def _format_error_payload(error: Exception) -> str:
    """Format one MCP CLI error as JSON.

    Args:
        error [Exception]: Error to render.

    Returns:
        str: JSON error payload.
    """
    payload: dict[str, object] = {"ok": False, "error": str(error)}
    error_payload: str = orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
    return error_payload


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


@mcp_app.command("serve")
def mcp_serve(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Default repository root used by omx-agent MCP command tools.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command recipe config path used by omx-agent MCP tools.",
    ),
    log_level: str = typer.Option(
        "ERROR",
        "--log-level",
        help="FastMCP log level for the stdio server.",
    ),
) -> None:
    """Serve omx-agent command tools over MCP stdio.

    Args:
        cwd [Path]: Default repository root.
        config_path [Path | None]: Optional command recipe config path.
        log_level [str]: FastMCP log level.
    """
    allowed_levels: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if log_level not in allowed_levels:
        raise typer.BadParameter(
            f"--log-level must be one of: {', '.join(allowed_levels)}"
        )
    run_omx_agent_mcp_stdio(
        cwd=cwd,
        config_path=config_path,
        log_level=cast(McpServeLogLevel, log_level),
    )


@mcp_app.command(
    "add",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def mcp_add(
    ctx: typer.Context,
    server_name: str = typer.Argument(
        ..., help="Repo-local MCP server id to register."
    ),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .comx-agent.toml or .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional config override, relative to --cwd when not absolute.",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        help="Streamable HTTP MCP URL. Omit when registering a stdio command.",
    ),
    bearer_token_env_var: str | None = typer.Option(
        None,
        "--bearer-token-env-var",
        help="Environment variable used for HTTP bearer auth.",
    ),
    env_values: list[str] | None = typer.Option(
        None,
        "--env",
        help="Stdio environment value in KEY=VALUE form. Repeatable.",
    ),
    env_vars: list[str] | None = typer.Option(
        None,
        "--env-var",
        help="Stdio environment variable name inherited from the agent shell. Repeatable.",
    ),
    enabled: bool = typer.Option(
        True, "--enabled/--disabled", help="Enable the repo-local server."
    ),
    startup_timeout_sec: float | None = typer.Option(
        None,
        "--startup-timeout-sec",
        help="Optional MCP startup timeout in seconds.",
    ),
    tool_timeout_sec: float | None = typer.Option(
        None,
        "--tool-timeout-sec",
        help="Optional MCP tool call timeout in seconds.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Replace an existing repo-local server."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Register a repo-local MCP server that comx-agent can consume.

    Args:
        ctx [typer.Context]: Typer context containing stdio command args.
        server_name [str]: Server id.
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        url [str | None]: HTTP MCP URL.
        bearer_token_env_var [str | None]: HTTP bearer token env var.
        env_values [list[str] | None]: KEY=VALUE environment pairs.
        env_vars [list[str] | None]: Inherited environment variable names.
        enabled [bool]: Whether the server is enabled.
        startup_timeout_sec [float | None]: Startup timeout.
        tool_timeout_sec [float | None]: Tool timeout.
        force [bool]: Whether to replace an existing server.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        command_args: tuple[str, ...] = tuple(ctx.args)
        if command_args and command_args[0] == "--":
            command_args = command_args[1:]
        if url is None and not command_args:
            raise ValueError("Pass --url for HTTP MCP or put a stdio command after --.")
        if url is not None and command_args:
            raise ValueError("Pass either --url or a stdio command after --, not both.")

        if url is not None:
            definition = RepoMcpServerDefinition(
                enabled=enabled,
                transport=McpTransportKind.STREAMABLE_HTTP,
                url=url,
                bearer_token_env_var=bearer_token_env_var,
                startup_timeout_sec=startup_timeout_sec,
                tool_timeout_sec=tool_timeout_sec,
            )
        else:
            definition = RepoMcpServerDefinition(
                enabled=enabled,
                transport=McpTransportKind.STDIO,
                command=command_args[0],
                args=command_args[1:],
                env=_env_pairs(env_values),
                env_vars=tuple(env_vars or ()),
                startup_timeout_sec=startup_timeout_sec,
                tool_timeout_sec=tool_timeout_sec,
            )
        result: McpServerRegistrationResult = register_repo_mcp_server(
            server_name,
            definition,
            cwd=cwd,
            config_path=config_path,
            force=force,
        )
    except (McpConfigWriteError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return
    typer.echo(_format_registration_human(result))


@mcp_app.command("remove")
def mcp_remove(
    server_name: str = typer.Argument(..., help="Repo-local MCP server id to remove."),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .comx-agent.toml or .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Optional config override."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Remove a repo-local MCP server registration.

    Args:
        server_name [str]: Server id.
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        result: McpServerRemovalResult = remove_repo_mcp_server(
            server_name,
            cwd=cwd,
            config_path=config_path,
        )
    except (McpConfigWriteError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return
    typer.echo(_format_removal_human(result))


@mcp_app.command("import-codex")
def mcp_import_codex(
    server_name: str = typer.Argument(
        ..., help="Codex MCP server id to copy repo-locally."
    ),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .comx-agent.toml or .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Optional config override."
    ),
    force: bool = typer.Option(
        False, "--force", help="Replace an existing repo-local server."
    ),
    enable: bool = typer.Option(
        True,
        "--enable/--preserve-enabled",
        help="Enable the repo-local copy even if Codex marks the source disabled.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Copy one server from Codex's MCP registry into repo-local config.

    Args:
        server_name [str]: Codex MCP server id.
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        force [bool]: Whether to replace an existing server.
        enable [bool]: Whether to force-enable the repo-local copy.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        result: McpServerRegistrationResult = import_codex_mcp_server(
            server_name,
            cwd=cwd,
            config_path=config_path,
            force=force,
            enable=enable,
        )
    except (McpConfigWriteError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return
    typer.echo(_format_registration_human(result))


@mcp_app.command("servers")
def mcp_servers(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .comx-agent.toml or .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional config override, relative to --cwd when not absolute.",
    ),
    include_codex: bool = typer.Option(
        True,
        "--codex/--no-codex",
        help="Include Codex MCP registry output from `codex mcp list --json`.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """List MCP servers comx-agent can consume as a client.

    Args:
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        include_codex [bool]: Whether to include Codex registry data.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        result: McpServerListResult = _read_registry(cwd, config_path, include_codex)
    except (ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_servers_human(result))


@mcp_app.command("tools")
def mcp_tools(
    server_name: str = typer.Argument(
        ..., help="MCP server name or source-qualified id."
    ),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve MCP config.",
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Optional config override."
    ),
    include_codex: bool = typer.Option(
        True, "--codex/--no-codex", help="Include Codex registry data."
    ),
    allow_disabled: bool = typer.Option(
        False,
        "--allow-disabled",
        help="Allow connecting to a server Codex marks disabled.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Connect to one MCP server and list tools.

    Args:
        server_name [str]: Server name to resolve.
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        include_codex [bool]: Whether to include Codex registry data.
        allow_disabled [bool]: Whether disabled servers may be contacted.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        registry: McpServerListResult = _read_registry(cwd, config_path, include_codex)
        server: McpServerConfig = resolve_mcp_server(registry.servers, server_name)
        _guard_disabled_server(server, allow_disabled)
        result: McpToolListResult = asyncio.run(list_mcp_tools(server))
    except (
        McpServerResolutionError,
        McpToolClientError,
        ValidationError,
        ValueError,
    ) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_tools_human(result))


@mcp_app.command("call")
def mcp_call(
    server_name: str = typer.Argument(
        ..., help="MCP server name or source-qualified id."
    ),
    tool_name: str = typer.Argument(..., help="MCP tool name."),
    cwd: Path = typer.Option(
        Path("."), "--cwd", help="Repository root used to resolve MCP config."
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Optional config override."
    ),
    include_codex: bool = typer.Option(
        True, "--codex/--no-codex", help="Include Codex registry data."
    ),
    arguments_json: str | None = typer.Option(
        None,
        "--arguments-json",
        help="JSON object passed as MCP tool arguments.",
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Actually call the tool. Omit for a dry-run plan.",
    ),
    allow_disabled: bool = typer.Option(
        False,
        "--allow-disabled",
        help="Allow connecting to a server Codex marks disabled.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Plan or execute one MCP tool call.

    Args:
        server_name [str]: Server name to resolve.
        tool_name [str]: Tool name to call.
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        include_codex [bool]: Whether to include Codex registry data.
        arguments_json [str | None]: JSON argument object.
        execute [bool]: Whether to execute instead of dry-run.
        allow_disabled [bool]: Whether disabled servers may be contacted.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        arguments: JsonObject = _arguments_json(arguments_json)
        registry: McpServerListResult = _read_registry(cwd, config_path, include_codex)
        server: McpServerConfig = resolve_mcp_server(registry.servers, server_name)
        if not execute:
            plan = McpToolCallPlan(
                server=server,
                tool_name=tool_name,
                arguments=arguments,
                warnings=("Dry-run only. Pass --execute to call the MCP tool.",),
            )
            if json_output:
                typer.echo(plan.model_dump_json(indent=2))
            else:
                typer.echo(
                    f"dry_run: {server.qualified_name}.{tool_name} "
                    "not executed; pass --execute to call."
                )
            return

        _guard_disabled_server(server, allow_disabled)
        result: McpToolCallResult = asyncio.run(
            call_mcp_tool(server, tool_name, arguments)
        )
    except (
        McpServerResolutionError,
        McpToolClientError,
        ValidationError,
        ValueError,
    ) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"executed: {result.server.qualified_name}.{result.tool_name}")
