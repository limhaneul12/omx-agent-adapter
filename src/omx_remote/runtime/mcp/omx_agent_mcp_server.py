from pathlib import Path

from mcp.server.fastmcp import FastMCP

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.runtime.mcp.omx_agent_command_tools import (
    list_command_tools_payload,
    preview_command_tool_payload,
    safe_tool_error_payload,
    show_command_tool_payload,
)
from omx_remote.shared.omx_enums.mcp_enums import McpLogLevel, mcp_log_level_value

SERVER_INSTRUCTIONS = """omx-agent exposes omx-agent-adapter command recipes as MCP tools.
All workflow command tools return typed dry-run plans first; they do not directly execute native Codex or OMX commands.
Review blocked_reasons, risk, manual_commands, and next_actions before any handoff."""


def _call_cwd(default_cwd: Path, cwd: str | None) -> str:
    """Resolve per-call cwd override text.

    Args:
        default_cwd [Path]: Server default working directory.
        cwd [str | None]: Per-tool override.

    Returns:
        str: Effective cwd text.
    """
    if cwd is None:
        cwd_text = str(default_cwd)
        return cwd_text
    cwd_text = cwd
    return cwd_text


def _call_config_path(
    default_config_path: Path | None, config_path: str | None
) -> str | None:
    """Resolve per-call config override text.

    Args:
        default_config_path [Path | None]: Server default config path.
        config_path [str | None]: Per-tool override.

    Returns:
        str | None: Effective config path text.
    """
    if config_path is not None:
        config_text: str | None = config_path
        return config_text
    if default_config_path is None:
        missing_config: None = None
        return missing_config
    config_text = str(default_config_path)
    return config_text


def build_omx_agent_mcp_server(
    cwd: str | Path = ".",
    config_path: str | Path | None = None,
    log_level: McpLogLevel | str = McpLogLevel.ERROR,
) -> FastMCP:
    """Build the omx-agent MCP server.

    Args:
        cwd [str | Path]: Default repository root for command recipes.
        config_path [str | Path | None]: Optional default command config path.
        log_level [McpLogLevel | str]: FastMCP log level.

    Returns:
        FastMCP: Configured MCP server.
    """
    default_cwd = Path(cwd).expanduser().resolve()
    default_config_path = (
        None if config_path is None else Path(config_path).expanduser().resolve()
    )
    normalized_log_level = mcp_log_level_value(log_level)
    server = FastMCP(
        name="omx-agent",
        instructions=SERVER_INSTRUCTIONS,
        log_level=normalized_log_level,
    )

    @server.tool(
        name="omx_agent_list_commands",
        description="List omx-agent-adapter command recipes available through this repo.",
    )
    def omx_agent_list_commands(
        cwd: str | None = None,
        config_path: str | None = None,
    ) -> JsonObject:
        """List command recipes.

        Args:
            cwd [str | None]: Optional repo root override.
            config_path [str | None]: Optional command config override.

        Returns:
            JsonObject: Command catalog payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        effective_config = _call_config_path(default_config_path, config_path)
        try:
            payload = list_command_tools_payload(
                cwd=effective_cwd,
                config_path=effective_config,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    @server.tool(
        name="omx_agent_show_command",
        description="Show one omx-agent command recipe by short or qualified command id.",
    )
    def omx_agent_show_command(
        command_id: str,
        cwd: str | None = None,
        config_path: str | None = None,
    ) -> JsonObject:
        """Show one command recipe.

        Args:
            command_id [str]: Short or qualified command id.
            cwd [str | None]: Optional repo root override.
            config_path [str | None]: Optional command config override.

        Returns:
            JsonObject: Command recipe payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        effective_config = _call_config_path(default_config_path, config_path)
        try:
            payload = show_command_tool_payload(
                cwd=effective_cwd,
                config_path=effective_config,
                command_id=command_id,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    @server.tool(
        name="omx_agent_preview_command",
        description=(
            "Preview any omx-agent command recipe as a typed dry-run plan. "
            "Accepts optional objective/topic/rubric/slug/prd_path context."
        ),
    )
    def omx_agent_preview_command(
        command_id: str,
        objective: str | None = None,
        topic: str | None = None,
        rubric: str | None = None,
        slug: str | None = None,
        prd_path: str | None = None,
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
        config_path: str | None = None,
    ) -> JsonObject:
        """Preview one command recipe.

        Args:
            command_id [str]: Short or qualified command id.
            objective [str | None]: User objective.
            topic [str | None]: Research topic.
            rubric [str | None]: Research rubric.
            slug [str | None]: Durable run slug.
            prd_path [str | None]: PRD or brief path.
            notes [str | None]: Additional notes.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.
            config_path [str | None]: Optional command config override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        effective_config = _call_config_path(default_config_path, config_path)
        try:
            payload = preview_command_tool_payload(
                cwd=effective_cwd,
                config_path=effective_config,
                command_id=command_id,
                objective=objective,
                topic=topic,
                rubric=rubric,
                slug=slug,
                prd_path=prd_path,
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    @server.tool(
        name="codex_deep_research",
        description="Preview the custom codex-deep-research workflow with an objective.",
    )
    def codex_deep_research(
        objective: str,
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview codex-deep-research.

        Args:
            objective [str]: Research objective.
            notes [str | None]: Additional notes.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=effective_cwd,
                config_path=str(default_config_path) if default_config_path else None,
                command_id="builtin:codex-deep-research",
                objective=objective,
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    @server.tool(
        name="omx_autoresearch_loop",
        description="Preview the custom omx-autoresearch-loop workflow with topic/rubric context.",
    )
    def omx_autoresearch_loop(
        topic: str,
        rubric: str | None = None,
        slug: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview omx-autoresearch-loop.

        Args:
            topic [str]: Durable research topic.
            rubric [str | None]: Critic rubric.
            slug [str | None]: Durable research slug.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=effective_cwd,
                config_path=str(default_config_path) if default_config_path else None,
                command_id="builtin:omx-autoresearch-loop",
                topic=topic,
                rubric=rubric,
                slug=slug,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    @server.tool(
        name="research_interview_prd",
        description="Preview the custom research-interview-prd workflow from an ambiguous objective.",
    )
    def research_interview_prd(
        objective: str,
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview research-interview-prd.

        Args:
            objective [str]: Product/research objective.
            notes [str | None]: Additional constraints or context.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=effective_cwd,
                config_path=str(default_config_path) if default_config_path else None,
                command_id="builtin:research-interview-prd",
                objective=objective,
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    @server.tool(
        name="verify_handoff_plus",
        description="Preview the custom verify-handoff-plus final verification workflow.",
    )
    def verify_handoff_plus(
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview verify-handoff-plus.

        Args:
            notes [str | None]: Optional review context.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        effective_cwd = _call_cwd(default_cwd, cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=effective_cwd,
                config_path=str(default_config_path) if default_config_path else None,
                command_id="builtin:verify-handoff-plus",
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=effective_cwd)
        return payload

    return server


def run_omx_agent_mcp_stdio(
    cwd: str | Path = ".",
    config_path: str | Path | None = None,
    log_level: McpLogLevel | str = McpLogLevel.ERROR,
) -> None:
    """Run the omx-agent MCP server over stdio.

    Args:
        cwd [str | Path]: Default repository root.
        config_path [str | Path | None]: Optional command config path.
        log_level [McpLogLevel | str]: FastMCP log level.
    """
    server = build_omx_agent_mcp_server(
        cwd=cwd,
        config_path=config_path,
        log_level=log_level,
    )
    server.run("stdio")
