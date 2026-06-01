import re
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from omx_remote.runtime.mcp.mcp_config_loader import (
    load_repo_mcp_servers,
    resolve_mcp_config_path,
)
from omx_remote.runtime.mcp.mcp_transport_resolution import (
    infer_repo_mcp_transport_kind,
)
from omx_remote.schemas.mcp.client_schemas import (
    McpServerConfig,
    McpServerRegistrationResult,
    McpServerRemovalResult,
    McpTransportKind,
    RepoMcpServerDefinition,
)
from omx_remote.shared.utils.toml_rendering import (
    toml_array,
    toml_inline_table,
    toml_string,
)

MCP_SERVER_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
)
MCP_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*\[([A-Za-z0-9_.-]+)\]\s*(?:#.*)?$"
)


class McpConfigWriteError(ValueError):
    """Raised when a repo-local MCP config cannot be written safely."""


def validate_repo_mcp_server_name(server_name: str) -> str:
    """Validate a repo-local MCP server id that can be rendered as TOML.

    Args:
        server_name [str]: Requested server id.

    Returns:
        str: Validated server id.
    """
    if MCP_SERVER_NAME_PATTERN.fullmatch(server_name) is None:
        raise McpConfigWriteError(
            "MCP server names must use only letters, numbers, '-' or '_', "
            "and must start with a letter or number."
        )
    return server_name


def validate_repo_definition(definition: RepoMcpServerDefinition) -> None:
    """Validate writer-only constraints before persisting a server.

    Args:
        definition [RepoMcpServerDefinition]: Candidate server definition.
    """
    transport_kind: McpTransportKind = infer_repo_mcp_transport_kind(definition)
    if transport_kind == McpTransportKind.STDIO:
        if definition.command is None:
            raise McpConfigWriteError("stdio MCP registration requires a command.")
        if definition.url is not None or definition.bearer_token_env_var is not None:
            raise McpConfigWriteError(
                "stdio MCP registration cannot include url or bearer token fields."
            )
        return

    if definition.url is None:
        raise McpConfigWriteError("streamable_http MCP registration requires --url.")
    if (
        definition.command is not None
        or definition.args
        or definition.env
        or definition.env_vars
        or definition.cwd is not None
    ):
        raise McpConfigWriteError(
            "streamable_http MCP registration cannot include stdio command fields."
        )


def render_repo_server_block(
    server_name: str,
    definition: RepoMcpServerDefinition,
) -> str:
    """Render one `[mcp.servers.<name>]` TOML block.

    Args:
        server_name [str]: Validated server id.
        definition [RepoMcpServerDefinition]: Server definition.

    Returns:
        str: TOML block.
    """
    transport_kind: McpTransportKind = infer_repo_mcp_transport_kind(definition)
    lines: list[str] = [
        f"[mcp.servers.{server_name}]",
        f"enabled = {'true' if definition.enabled else 'false'}",
        f"transport = {toml_string(transport_kind)}",
    ]
    if definition.command is not None:
        lines.append(f"command = {toml_string(definition.command)}")
    if definition.args:
        lines.append(f"args = {toml_array(definition.args)}")
    if definition.env:
        lines.append(f"env = {toml_inline_table(definition.env)}")
    if definition.env_vars:
        lines.append(f"env_vars = {toml_array(definition.env_vars)}")
    if definition.cwd is not None:
        lines.append(f"cwd = {toml_string(definition.cwd)}")
    if definition.url is not None:
        lines.append(f"url = {toml_string(definition.url)}")
    if definition.bearer_token_env_var is not None:
        lines.append(
            f"bearer_token_env_var = {toml_string(definition.bearer_token_env_var)}"
        )
    if definition.startup_timeout_sec is not None:
        lines.append(f"startup_timeout_sec = {definition.startup_timeout_sec:g}")
    if definition.tool_timeout_sec is not None:
        lines.append(f"tool_timeout_sec = {definition.tool_timeout_sec:g}")

    rendered_block: str = "\n".join(lines) + "\n"
    return rendered_block


def load_existing_repo_servers(config_path: Path) -> tuple[McpServerConfig, ...]:
    """Load existing repo MCP servers from the target config path.

    Args:
        config_path [Path]: Config path.

    Returns:
        tuple[McpServerConfig, ...]: Existing repo servers.
    """
    if not config_path.exists():
        empty_servers: tuple[McpServerConfig, ...] = ()
        return empty_servers
    servers: tuple[McpServerConfig, ...] = load_repo_mcp_servers(
        cwd=config_path.parent,
        config_path=config_path,
    )
    return servers


def find_repo_server(
    servers: tuple[McpServerConfig, ...],
    server_name: str,
) -> McpServerConfig | None:
    """Find one repo server by short name.

    Args:
        servers [tuple[McpServerConfig, ...]]: Repo servers.
        server_name [str]: Server id.

    Returns:
        McpServerConfig | None: Matched server.
    """
    for server in servers:
        if server.name == server_name:
            return server
    return None


def _remove_server_blocks_from_text(text: str, server_name: str) -> tuple[str, bool]:
    """Remove TOML server blocks that target one MCP server id.

    Args:
        text [str]: Existing TOML content.
        server_name [str]: Server id.

    Returns:
        tuple[str, bool]: Updated text and whether a block was removed.
    """
    target_sections: set[str] = {
        f"mcp.servers.{server_name}",
        f"mcp_servers.{server_name}",
    }
    filtered_lines: list[str] = []
    skip_current_section = False
    removed = False

    for line in text.splitlines(keepends=True):
        section_match = MCP_SECTION_PATTERN.match(line)
        if section_match is not None:
            section_name: str = section_match.group(1)
            if section_name in target_sections:
                skip_current_section = True
                removed = True
                continue
            skip_current_section = False
        if not skip_current_section:
            filtered_lines.append(line)

    updated_text: str = "".join(filtered_lines).rstrip()
    if updated_text:
        updated_text += "\n"
    return updated_text, removed


def remove_repo_mcp_server(
    server_name: str,
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> McpServerRemovalResult:
    """Remove one repo-local MCP server block from the config file.

    Args:
        server_name [str]: Server id.
        cwd [str | Path | None]: Base directory.
        config_path [str | Path | None]: Optional config override.

    Returns:
        McpServerRemovalResult: Removal result.
    """
    validated_name: str = validate_repo_mcp_server_name(server_name)
    resolved_config_path: Path = resolve_mcp_config_path(
        cwd=cwd,
        config_path=config_path,
    )
    if not resolved_config_path.exists():
        return McpServerRemovalResult(
            server_name=validated_name,
            config_path=str(resolved_config_path),
            removed=False,
            warnings=("No repo-local MCP config file exists.",),
        )

    config_text: str = resolved_config_path.read_text(encoding="utf-8")
    updated_text, removed = _remove_server_blocks_from_text(config_text, validated_name)
    if removed:
        resolved_config_path.write_text(updated_text, encoding="utf-8")

    warnings: tuple[str, ...] = ()
    if not removed:
        warnings = ("No matching repo-local MCP server block was found.",)
    return McpServerRemovalResult(
        server_name=validated_name,
        config_path=str(resolved_config_path),
        removed=removed,
        warnings=warnings,
    )


def register_repo_mcp_server(
    server_name: str,
    definition: RepoMcpServerDefinition,
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
    force: bool = False,
    warnings: Iterable[str] = (),
) -> McpServerRegistrationResult:
    """Register one MCP server in repo-local comx-agent config.

    Args:
        server_name [str]: Server id.
        definition [RepoMcpServerDefinition]: Server definition.
        cwd [str | Path | None]: Base directory.
        config_path [str | Path | None]: Optional config override.
        force [bool]: Replace an existing repo-local server with the same id.
        warnings [Iterable[str]]: Additional result warnings.

    Returns:
        McpServerRegistrationResult: Registration result.
    """
    validated_name: str = validate_repo_mcp_server_name(server_name)
    validate_repo_definition(definition)
    resolved_config_path: Path = resolve_mcp_config_path(
        cwd=cwd,
        config_path=config_path,
    )
    created_config: bool = not resolved_config_path.exists()
    existing_servers: tuple[McpServerConfig, ...] = load_existing_repo_servers(
        resolved_config_path
    )
    replaced_existing = False
    if find_repo_server(existing_servers, validated_name) is not None:
        if not force:
            raise McpConfigWriteError(
                f"Repo-local MCP server {validated_name!r} already exists; pass --force to replace it."
            )
        removal_result: McpServerRemovalResult = remove_repo_mcp_server(
            validated_name,
            cwd=resolved_config_path.parent,
            config_path=resolved_config_path,
        )
        replaced_existing = removal_result.removed

    rendered_block: str = render_repo_server_block(validated_name, definition)
    resolved_config_path.parent.mkdir(parents=True, exist_ok=True)
    if resolved_config_path.exists():
        existing_text: str = resolved_config_path.read_text(encoding="utf-8").rstrip()
        if existing_text:
            next_text: str = existing_text + "\n\n" + rendered_block
        else:
            next_text = rendered_block
    else:
        next_text = rendered_block
    resolved_config_path.write_text(next_text, encoding="utf-8")

    reloaded_servers: tuple[McpServerConfig, ...] = load_existing_repo_servers(
        resolved_config_path
    )
    registered_server: McpServerConfig | None = find_repo_server(
        reloaded_servers,
        validated_name,
    )
    if registered_server is None:
        raise McpConfigWriteError(
            f"Repo-local MCP server {validated_name!r} was written but could not be reloaded."
        )

    return McpServerRegistrationResult(
        server=registered_server,
        config_path=str(resolved_config_path),
        created_config=created_config,
        replaced_existing=replaced_existing,
        warnings=tuple(warnings),
    )
