from pathlib import Path

from mcp.server.fastmcp import FastMCP

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.runtime.mcp.omx_agent_command_tools import (
    list_command_tools_payload,
    preview_command_tool_payload,
    safe_tool_error_payload,
    show_command_tool_payload,
)
from omx_remote.runtime.mcp.omx_agent_company_run_server_tools import (
    register_company_run_tools,
)
from omx_remote.runtime.mcp.omx_agent_mcp_call_context import (
    effective_config_path,
    effective_cwd,
)
from omx_remote.shared.omx_enums.mcp_enums import McpLogLevel, mcp_log_level_value

SERVER_INSTRUCTIONS = """omx-agent exposes omx-agent-adapter command recipes as MCP tools.
Preview tools return typed dry-run plans and do not execute native Codex or OMX commands.
company_run_execute is the explicit actual execution tool for the real company-run engine.
Review blocked_reasons, risk, manual_commands, next_actions, run_id, status, and artifact paths before any handoff."""


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
        call_cwd = effective_cwd(default_cwd=default_cwd, cwd=cwd)
        call_config = effective_config_path(
            default_config_path=default_config_path, config_path=config_path
        )
        try:
            payload = list_command_tools_payload(
                cwd=call_cwd,
                config_path=call_config,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
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
        call_cwd = effective_cwd(default_cwd=default_cwd, cwd=cwd)
        call_config = effective_config_path(
            default_config_path=default_config_path, config_path=config_path
        )
        try:
            payload = show_command_tool_payload(
                cwd=call_cwd,
                config_path=call_config,
                command_id=command_id,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
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
        call_cwd = effective_cwd(default_cwd=default_cwd, cwd=cwd)
        call_config = effective_config_path(
            default_config_path=default_config_path, config_path=config_path
        )
        try:
            payload = preview_command_tool_payload(
                cwd=call_cwd,
                config_path=call_config,
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
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    @server.tool(
        name="research_brief",
        description="Preview the canonical research-brief workflow with an objective.",
    )
    def research_brief(
        objective: str,
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview research-brief.

        Args:
            objective [str]: Research objective.
            notes [str | None]: Additional notes.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        call_cwd = effective_cwd(default_cwd=default_cwd, cwd=cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=call_cwd,
                config_path=str(default_config_path)
                if default_config_path is not None
                else None,
                command_id="builtin:research-brief",
                objective=objective,
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    @server.tool(
        name="idea_to_prd",
        description="Preview the canonical idea-to-prd planning workflow.",
    )
    def idea_to_prd(
        objective: str,
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview idea-to-prd.

        Args:
            objective [str]: Product or feature objective.
            notes [str | None]: Additional constraints or context.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        call_cwd = effective_cwd(default_cwd=default_cwd, cwd=cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=call_cwd,
                config_path=str(default_config_path)
                if default_config_path is not None
                else None,
                command_id="builtin:idea-to-prd",
                objective=objective,
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    @server.tool(
        name="release_readiness",
        description="Preview the canonical release-readiness workflow.",
    )
    def release_readiness(
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview release-readiness.

        Args:
            notes [str | None]: Optional release context.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        call_cwd = effective_cwd(default_cwd=default_cwd, cwd=cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=call_cwd,
                config_path=str(default_config_path)
                if default_config_path is not None
                else None,
                command_id="builtin:release-readiness",
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    register_company_run_tools(
        server=server,
        default_cwd=default_cwd,
        default_config_path=default_config_path,
    )

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
