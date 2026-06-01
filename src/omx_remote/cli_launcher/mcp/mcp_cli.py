import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.cli_launcher.mcp.mcp_cli_support import (
    _arguments_json,
    _format_registration_human,
    _format_removal_human,
    _format_servers_human,
    _format_tools_human,
    _guard_disabled_server,
    _read_registry,
)
from omx_remote.cli_launcher.mcp.mcp_registration_cli import mcp_add
from omx_remote.runtime.mcp.mcp_config_writer import (
    McpConfigWriteError,
    remove_repo_mcp_server,
)
from omx_remote.runtime.mcp.mcp_registry_reader import (
    McpServerResolutionError,
    resolve_mcp_server,
)
from omx_remote.runtime.mcp.mcp_server_registration import (
    import_codex_mcp_server,
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
)
from omx_remote.shared.omx_enums.mcp_enums import McpLogLevel

mcp_app = typer.Typer(
    help="Consume external MCP servers/tools like Codex, or serve omx-agent tools.",
    add_completion=False,
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
    log_level: McpLogLevel = typer.Option(
        McpLogLevel.ERROR,
        "--log-level",
        help="FastMCP log level for the stdio server.",
    ),
) -> None:
    """Serve omx-agent command tools over MCP stdio.

    Args:
        cwd [Path]: Default repository root.
        config_path [Path | None]: Optional command recipe config path.
        log_level [McpLogLevel]: FastMCP log level.
    """
    run_omx_agent_mcp_stdio(
        cwd=cwd,
        config_path=config_path,
        log_level=log_level,
    )


mcp_app.command(
    "add",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)(mcp_add)


@mcp_app.command("remove")
def mcp_remove(
    server_name: str = typer.Argument(..., help="Repo-local MCP server id to remove."),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .comx-agent.toml.",
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
        help="Repository root used to resolve .comx-agent.toml.",
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
        help="Repository root used to resolve .comx-agent.toml.",
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
