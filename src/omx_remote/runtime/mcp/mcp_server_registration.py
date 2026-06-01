from pathlib import Path

from omx_remote.runtime.mcp.codex_mcp_registry import read_codex_mcp_servers
from omx_remote.runtime.mcp.mcp_config_writer import (
    McpConfigWriteError,
    find_repo_server,
    register_repo_mcp_server,
    validate_repo_mcp_server_name,
)
from omx_remote.schemas.mcp.client_schemas import (
    McpServerConfig,
    McpServerRegistrationResult,
    McpTransportKind,
    RepoMcpServerDefinition,
)


def repo_definition_from_server(
    server: McpServerConfig,
    enabled: bool | None = None,
) -> RepoMcpServerDefinition:
    """Convert a discovered MCP server into a repo-local definition.

    Args:
        server [McpServerConfig]: Discovered server config.
        enabled [bool | None]: Optional enabled override.

    Returns:
        RepoMcpServerDefinition: Repo-local definition.
    """
    next_enabled: bool = server.enabled if enabled is None else enabled
    if server.transport.type == McpTransportKind.STDIO:
        env: dict[str, str] = {}
        env_var_names: list[str] = []
        for entry in server.transport.env:
            if entry.value is None:
                env_var_names.append(entry.name)
            else:
                env[entry.name] = entry.value
        for env_var_name in server.transport.env_vars:
            if env_var_name not in env and env_var_name not in env_var_names:
                env_var_names.append(env_var_name)

        definition = RepoMcpServerDefinition(
            enabled=next_enabled,
            transport=McpTransportKind.STDIO,
            command=server.transport.command,
            args=server.transport.args,
            env=env,
            env_vars=tuple(env_var_names),
            cwd=server.transport.cwd,
            startup_timeout_sec=server.startup_timeout_sec,
            tool_timeout_sec=server.tool_timeout_sec,
        )
        return definition

    definition = RepoMcpServerDefinition(
        enabled=next_enabled,
        transport=McpTransportKind.STREAMABLE_HTTP,
        url=server.transport.url,
        bearer_token_env_var=server.transport.bearer_token_env_var,
        startup_timeout_sec=server.startup_timeout_sec,
        tool_timeout_sec=server.tool_timeout_sec,
    )
    return definition


def import_codex_mcp_server(
    server_name: str,
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
    force: bool = False,
    enable: bool = True,
) -> McpServerRegistrationResult:
    """Copy one Codex MCP server registration into repo-local config.

    Args:
        server_name [str]: Codex MCP server id.
        cwd [str | Path | None]: Base directory.
        config_path [str | Path | None]: Optional config override.
        force [bool]: Replace existing repo-local server with same id.
        enable [bool]: Enable the repo-local copy even if Codex marks it disabled.

    Returns:
        McpServerRegistrationResult: Registration result.
    """
    validated_name: str = validate_repo_mcp_server_name(server_name)
    codex_servers: tuple[McpServerConfig, ...] = read_codex_mcp_servers()
    matched_server: McpServerConfig | None = find_repo_server(
        codex_servers,
        validated_name,
    )
    if matched_server is None:
        raise McpConfigWriteError(f"Codex MCP server {validated_name!r} was not found.")

    enabled_override: bool | None = True if enable else None
    definition: RepoMcpServerDefinition = repo_definition_from_server(
        matched_server,
        enabled=enabled_override,
    )
    result: McpServerRegistrationResult = register_repo_mcp_server(
        validated_name,
        definition,
        cwd=cwd,
        config_path=config_path,
        force=force,
        warnings=("Imported from Codex MCP registry.",),
    )
    return result
