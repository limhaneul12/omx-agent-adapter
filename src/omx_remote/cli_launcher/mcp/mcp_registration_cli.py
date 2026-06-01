from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.cli_launcher.mcp.mcp_cli_support import (
    _env_pairs,
    _format_registration_human,
)
from omx_remote.runtime.mcp.mcp_config_writer import (
    McpConfigWriteError,
    register_repo_mcp_server,
)
from omx_remote.schemas.mcp_client_schemas import (
    McpServerRegistrationResult,
    McpTransportKind,
    RepoMcpServerDefinition,
)


def mcp_add(
    ctx: typer.Context,
    server_name: str = typer.Argument(
        ..., help="Repo-local MCP server id to register."
    ),
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
            normalized_env_vars: tuple[str, ...]
            if env_vars is None:
                normalized_env_vars = ()
            else:
                normalized_env_vars = tuple(env_vars)
            definition = RepoMcpServerDefinition(
                enabled=enabled,
                transport=McpTransportKind.STDIO,
                command=command_args[0],
                args=command_args[1:],
                env=_env_pairs(env_values),
                env_vars=normalized_env_vars,
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
