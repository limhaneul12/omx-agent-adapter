"""MCP server tool registrations for explicit company-run operations."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.runtime.mcp.omx_agent_command_tools import (
    preview_command_tool_payload,
    safe_tool_error_payload,
)
from omx_remote.runtime.mcp.omx_agent_company_run_payloads import (
    company_run_artifacts_tool_payload,
    company_run_status_tool_payload,
    execute_company_run_tool_payload,
)
from omx_remote.runtime.mcp.omx_agent_mcp_call_context import (
    effective_config_path,
    effective_cwd,
)
from omx_remote.schemas.company_run_schemas import COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunCouncilMode,
    CompanyRunTeamLaunchMode,
)


def register_company_run_tools(
    server: FastMCP,
    default_cwd: Path,
    default_config_path: Path | None,
) -> None:
    """Register company-run preview, execute, status, and artifact tools.

    Args:
        server [FastMCP]: MCP server to register tools on.
        default_cwd [Path]: Server default repository root.
        default_config_path [Path | None]: Optional default config path.
    """

    @server.tool(
        name="company_run",
        description="Preview the company-run macro orchestration workflow.",
    )
    def company_run(
        objective: str,
        notes: str | None = None,
        record_run: bool = False,
        cwd: str | None = None,
    ) -> JsonObject:
        """Preview company-run.

        Args:
            objective [str]: Idea, goal, or product objective.
            notes [str | None]: Additional constraints or context.
            record_run [bool]: Whether to record the dry-run.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Dry-run command plan payload.
        """
        call_cwd = effective_cwd(default_cwd, cwd)
        try:
            payload = preview_command_tool_payload(
                cwd=call_cwd,
                config_path=str(default_config_path) if default_config_path else None,
                command_id="builtin:company-run",
                objective=objective,
                notes=notes,
                record_run=record_run,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    @server.tool(
        name="company_run_execute",
        description=(
            "Execute the real company-run engine with CEO/council votes, "
            "Team/subagent dispatch evidence, review gates, and artifacts."
        ),
    )
    def company_run_execute(
        objective: str,
        notes: str | None = None,
        live_team_allowed: bool = False,
        council_mode: str = CompanyRunCouncilMode.CODEX.value,
        team_launch_mode: str = CompanyRunTeamLaunchMode.LAUNCH.value,
        worker_count: int = 4,
        timeout_seconds: float = COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS,
        cwd: str | None = None,
        config_path: str | None = None,
    ) -> JsonObject:
        """Execute company-run through the explicit actual MCP tool.

        Args:
            objective [str]: Company-run objective.
            notes [str | None]: Additional context.
            live_team_allowed [bool]: Whether live OMX Team launch is allowed.
            council_mode [str]: Council/subagent execution mode.
            team_launch_mode [str]: Team handling mode.
            worker_count [int]: Team worker count.
            timeout_seconds [float]: Runtime timeout.
            cwd [str | None]: Optional repo root override.
            config_path [str | None]: Optional config override.

        Returns:
            JsonObject: Actual company-run payload.
        """
        call_cwd = effective_cwd(default_cwd, cwd)
        call_config = effective_config_path(default_config_path, config_path)
        try:
            payload = execute_company_run_tool_payload(
                cwd=call_cwd,
                config_path=call_config,
                objective=objective,
                notes=notes,
                live_team_allowed=live_team_allowed,
                council_mode=council_mode,
                team_launch_mode=team_launch_mode,
                worker_count=worker_count,
                timeout_seconds=timeout_seconds,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    @server.tool(
        name="company_run_status",
        description="Read status for one actual company-run run id.",
    )
    def company_run_status(
        run_id: str,
        cwd: str | None = None,
    ) -> JsonObject:
        """Read company-run status.

        Args:
            run_id [str]: Actual run id.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Company-run status payload.
        """
        call_cwd = effective_cwd(default_cwd, cwd)
        try:
            payload = company_run_status_tool_payload(
                cwd=call_cwd,
                run_id=run_id,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload

    @server.tool(
        name="company_run_artifacts",
        description="List and read artifacts for one actual company-run run id.",
    )
    def company_run_artifacts(
        run_id: str,
        cwd: str | None = None,
    ) -> JsonObject:
        """Read company-run artifacts.

        Args:
            run_id [str]: Actual run id.
            cwd [str | None]: Optional repo root override.

        Returns:
            JsonObject: Company-run artifact payload.
        """
        call_cwd = effective_cwd(default_cwd, cwd)
        try:
            payload = company_run_artifacts_tool_payload(
                cwd=call_cwd,
                run_id=run_id,
            )
        except Exception as error:  # dynamic MCP tool boundary
            payload = safe_tool_error_payload(error, cwd=call_cwd)
        return payload
