import tomllib
from pathlib import Path
from typing import Final

from omx_remote.runtime.agents.agent_config_loader import DEFAULT_AGENT_CONFIG_FILENAME
from omx_remote.runtime.mcp.mcp_transport_resolution import (
    infer_repo_mcp_transport_kind,
)
from omx_remote.schemas.mcp.client_schemas import (
    McpEnvironmentVariable,
    McpServerConfig,
    McpServerSource,
    McpServerTransport,
    McpTransportKind,
    RepoMcpServerDefinition,
)

COMX_AGENT_CONFIG_FILENAME: Final[str] = ".comx-agent.toml"
MCP_TOP_LEVEL_SECTION: Final[str] = "mcp"
CODEX_MCP_TOP_LEVEL_SECTION: Final[str] = "mcp_servers"


class McpConfigLoadError(ValueError):
    """Raised when repo-local MCP configuration cannot be loaded."""


def resolve_mcp_config_path(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> Path:
    """Resolve the repo-local comx/agent config path for MCP sections.

    Args:
        cwd [str | Path | None]: Base working directory.
        config_path [str | Path | None]: Optional config path override.

    Returns:
        Path: Config path to inspect.
    """
    root_path: Path = Path.cwd() if cwd is None else Path(cwd)
    if config_path is not None:
        candidate_path = Path(config_path)
        if candidate_path.is_absolute():
            resolved_path: Path = candidate_path
            return resolved_path
        resolved_path = root_path / candidate_path
        return resolved_path

    comx_config_path: Path = root_path / COMX_AGENT_CONFIG_FILENAME
    if comx_config_path.exists():
        return comx_config_path

    agent_remote_config_path: Path = root_path / DEFAULT_AGENT_CONFIG_FILENAME
    return agent_remote_config_path


def _load_toml_object(config_path: Path) -> dict[str, object]:
    """Load one TOML file into a raw object.

    Args:
        config_path [Path]: TOML path.

    Returns:
        dict[str, object]: Parsed TOML root object.
    """
    try:
        config_text: str = config_path.read_text(encoding="utf-8")
        parsed_toml: dict[str, object] = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        raise McpConfigLoadError(
            f"MCP config at {config_path} contains malformed TOML: {error}"
        ) from error
    except OSError as error:
        raise McpConfigLoadError(
            f"MCP config at {config_path} could not be read: {error}"
        ) from error

    return parsed_toml


def _definition_to_server(
    server_name: str,
    definition: RepoMcpServerDefinition,
) -> McpServerConfig:
    """Convert one repo TOML server definition into a stable config.

    Args:
        server_name [str]: MCP server id from the TOML table.
        definition [RepoMcpServerDefinition]: Validated repo definition.

    Returns:
        McpServerConfig: Stable server config.
    """
    transport_kind: McpTransportKind = infer_repo_mcp_transport_kind(definition)
    env: tuple[McpEnvironmentVariable, ...] = tuple(
        McpEnvironmentVariable(name=name, value=value)
        for name, value in sorted(definition.env.items())
    )
    transport = McpServerTransport(
        type=transport_kind,
        command=definition.command,
        args=definition.args,
        env=env,
        env_vars=definition.env_vars,
        cwd=definition.cwd,
        url=definition.url,
        bearer_token_env_var=definition.bearer_token_env_var,
    )
    server = McpServerConfig(
        name=server_name,
        source=McpServerSource.REPO,
        enabled=definition.enabled,
        transport=transport,
        startup_timeout_sec=definition.startup_timeout_sec,
        tool_timeout_sec=definition.tool_timeout_sec,
    )
    return server


def _load_nested_mcp_servers(
    parsed_toml: dict[str, object],
    config_path: Path,
) -> tuple[McpServerConfig, ...]:
    """Load repo-local `[mcp.servers.<name>]` server definitions.

    Args:
        parsed_toml [dict[str, object]]: Parsed TOML root object.
        config_path [Path]: Source path for diagnostics.

    Returns:
        tuple[McpServerConfig, ...]: Loaded server configs.
    """
    raw_mcp_section: object = parsed_toml.get(MCP_TOP_LEVEL_SECTION, {})
    if not isinstance(raw_mcp_section, dict):
        raise McpConfigLoadError(
            f"MCP config at {config_path} must define [mcp] as a TOML table."
        )

    raw_servers_section: object = raw_mcp_section.get("servers", {})
    if not isinstance(raw_servers_section, dict):
        raise McpConfigLoadError(
            f"MCP config at {config_path} must define [mcp.servers] as a TOML table."
        )

    servers: list[McpServerConfig] = []
    for server_name, raw_server_payload in raw_servers_section.items():
        if not isinstance(server_name, str):
            raise McpConfigLoadError(
                f"MCP config at {config_path} contains a non-string server id."
            )
        if not isinstance(raw_server_payload, dict):
            raise McpConfigLoadError(
                f"MCP config at {config_path} must define [mcp.servers.{server_name}] as a TOML table."
            )
        definition = RepoMcpServerDefinition.model_validate(raw_server_payload)
        server: McpServerConfig = _definition_to_server(server_name, definition)
        servers.append(server)

    loaded_servers: tuple[McpServerConfig, ...] = tuple(servers)
    return loaded_servers


def _load_codex_style_repo_servers(
    parsed_toml: dict[str, object],
    config_path: Path,
) -> tuple[McpServerConfig, ...]:
    """Load repo-local Codex-style `[mcp_servers.<name>]` definitions.

    Args:
        parsed_toml [dict[str, object]]: Parsed TOML root object.
        config_path [Path]: Source path for diagnostics.

    Returns:
        tuple[McpServerConfig, ...]: Loaded server configs.
    """
    raw_servers_section: object = parsed_toml.get(CODEX_MCP_TOP_LEVEL_SECTION, {})
    if not isinstance(raw_servers_section, dict):
        raise McpConfigLoadError(
            f"MCP config at {config_path} must define [mcp_servers] as a TOML table."
        )

    servers: list[McpServerConfig] = []
    for server_name, raw_server_payload in raw_servers_section.items():
        if not isinstance(server_name, str):
            raise McpConfigLoadError(
                f"MCP config at {config_path} contains a non-string Codex MCP server id."
            )
        if not isinstance(raw_server_payload, dict):
            raise McpConfigLoadError(
                f"MCP config at {config_path} must define [mcp_servers.{server_name}] as a TOML table."
            )
        definition = RepoMcpServerDefinition.model_validate(raw_server_payload)
        server: McpServerConfig = _definition_to_server(server_name, definition)
        servers.append(server)

    loaded_servers: tuple[McpServerConfig, ...] = tuple(servers)
    return loaded_servers


def load_repo_mcp_servers(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> tuple[McpServerConfig, ...]:
    """Load repo-local MCP server configs for comx-agent client use.

    Args:
        cwd [str | Path | None]: Base working directory.
        config_path [str | Path | None]: Optional config path override.

    Returns:
        tuple[McpServerConfig, ...]: Repo-defined MCP server configs.
    """
    resolved_config_path: Path = resolve_mcp_config_path(cwd=cwd, config_path=config_path)
    if not resolved_config_path.exists():
        empty_servers: tuple[McpServerConfig, ...] = ()
        return empty_servers

    parsed_toml: dict[str, object] = _load_toml_object(resolved_config_path)
    nested_servers: tuple[McpServerConfig, ...] = _load_nested_mcp_servers(
        parsed_toml,
        resolved_config_path,
    )
    codex_style_servers: tuple[McpServerConfig, ...] = _load_codex_style_repo_servers(
        parsed_toml,
        resolved_config_path,
    )
    repo_servers: tuple[McpServerConfig, ...] = (*nested_servers, *codex_style_servers)
    return repo_servers
