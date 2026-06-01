from pathlib import Path

from omx_remote.runtime.mcp.codex_mcp_registry import (
    CodexMcpRegistryError,
    read_codex_mcp_servers,
)
from omx_remote.runtime.mcp.mcp_config_loader import (
    McpConfigLoadError,
    load_repo_mcp_servers,
)
from omx_remote.schemas.mcp_client_schemas import (
    McpServerConfig,
    McpServerListResult,
    McpServerSource,
)


class McpServerResolutionError(ValueError):
    """Raised when an MCP server name cannot be resolved safely."""


def read_mcp_servers(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
    include_codex: bool = True,
) -> McpServerListResult:
    """Read MCP servers from Codex and repo-local comx/agent config.

    Args:
        cwd [str | Path | None]: Base working directory.
        config_path [str | Path | None]: Optional repo config override.
        include_codex [bool]: Whether to include Codex's MCP registry.

    Returns:
        McpServerListResult: Typed server registry.
    """
    warnings: list[str] = []
    codex_servers: tuple[McpServerConfig, ...] = ()
    repo_servers: tuple[McpServerConfig, ...] = ()

    if include_codex:
        try:
            codex_servers = read_codex_mcp_servers()
        except CodexMcpRegistryError as error:
            warnings.append(str(error))

    try:
        repo_servers = load_repo_mcp_servers(cwd=cwd, config_path=config_path)
    except McpConfigLoadError as error:
        warnings.append(str(error))

    servers: tuple[McpServerConfig, ...] = (*codex_servers, *repo_servers)
    result = McpServerListResult(
        servers=servers,
        codex_count=len(codex_servers),
        repo_count=len(repo_servers),
        enabled_count=sum(1 for server in servers if server.enabled),
        warnings=tuple(warnings),
    )
    return result


def resolve_mcp_server(
    servers: tuple[McpServerConfig, ...],
    server_name: str,
) -> McpServerConfig:
    """Resolve an MCP server by source-qualified or unambiguous short name.

    Args:
        servers [tuple[McpServerConfig, ...]]: Available server configs.
        server_name [str]: Requested server name.

    Returns:
        McpServerConfig: Resolved server config.
    """
    if ":" in server_name:
        for server in servers:
            if server.qualified_name == server_name:
                resolved_server: McpServerConfig = server
                return resolved_server
        raise McpServerResolutionError(f"No MCP server named {server_name} was found.")

    repo_matches: tuple[McpServerConfig, ...] = tuple(
        server
        for server in servers
        if server.name == server_name and server.source == McpServerSource.REPO
    )
    codex_matches: tuple[McpServerConfig, ...] = tuple(
        server
        for server in servers
        if server.name == server_name and server.source == McpServerSource.CODEX
    )
    matches: tuple[McpServerConfig, ...] = (*repo_matches, *codex_matches)
    if len(matches) == 1:
        resolved_server = matches[0]
        return resolved_server
    if not matches:
        raise McpServerResolutionError(f"No MCP server named {server_name} was found.")

    qualified_names: str = ", ".join(server.qualified_name for server in matches)
    raise McpServerResolutionError(
        f"MCP server id {server_name} is ambiguous; choose one of: {qualified_names}."
    )
