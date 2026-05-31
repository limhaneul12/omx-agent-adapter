from pathlib import Path

from omx_remote.runtime.comx.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.runtime.comx.research_workflow import create_research_workflow_plan
from omx_remote.runtime.comx.tui_command_catalog import (
    find_tui_slash_command,
    format_tui_slash_command_help,
    get_tui_slash_command_args,
)
from omx_remote.runtime.comx.tui_command_workbench import (
    build_tui_commands_result,
    build_tui_recipe_preview_result,
)
from omx_remote.runtime.comx.tui_mcp_panels import build_tui_mcp_result
from omx_remote.runtime.mcp.mcp_registry_reader import read_mcp_servers
from omx_remote.schemas.comx.control_surface_schemas import ComxControlSurfaceInventory
from omx_remote.schemas.comx.research_workflow_schemas import ComxResearchWorkflowPlan
from omx_remote.schemas.comx.session_schemas import ComxTuiSessionRecord
from omx_remote.schemas.comx.tui_schemas import (
    ComxTuiCommandResult,
    ComxTuiSlashCommand,
)
from omx_remote.schemas.mcp.client_schemas import McpServerListResult
from omx_remote.schemas.next.next_action_schemas import NextActionResult


def _status_result(
    cwd: Path, next_action: NextActionResult | None
) -> ComxTuiCommandResult:
    """Build a status result.

    Args:
        cwd [Path]: Workspace root.
        next_action [NextActionResult | None]: Optional next action.

    Returns:
        ComxTuiCommandResult: Result.
    """
    inventory: ComxControlSurfaceInventory = build_comx_control_surface_inventory(
        cwd=cwd
    )
    registry: McpServerListResult = read_mcp_servers(cwd=cwd)
    next_summary: str = "not loaded"
    if next_action is not None:
        next_summary = next_action.summary

    body: str = "\n".join(
        (
            f"workspace: {cwd.resolve()}",
            f"native_commands: {inventory.native_count}",
            f"composed_commands: {inventory.composed_count}",
            f"mcp_servers: {len(registry.servers)} enabled={registry.enabled_count}",
            f"next_action: {next_summary}",
            "safe defaults: read-only panels and dry-run command previews",
        )
    )
    result = ComxTuiCommandResult(
        command="/status",
        title="comx-agent status",
        body=body,
        warnings=registry.warnings,
    )
    return result


def _surface_result(command_name: str, workspace: Path) -> ComxTuiCommandResult:
    """Build a control-surface summary result.

    Args:
        command_name [str]: Slash command name.
        workspace [Path]: Workspace root.

    Returns:
        ComxTuiCommandResult: Control surface result.
    """
    inventory: ComxControlSurfaceInventory = build_comx_control_surface_inventory(
        cwd=workspace
    )
    result = ComxTuiCommandResult(
        command=command_name,
        title="control surface",
        body=(
            f"native={inventory.native_count} composed={inventory.composed_count}\n"
            "Use /commands to inspect composed recipes."
        ),
    )
    return result


def _route_result(command_name: str, args: str) -> ComxTuiCommandResult:
    """Build a typed-route preview result.

    Args:
        command_name [str]: Slash command name.
        args [str]: Inline route task text.

    Returns:
        ComxTuiCommandResult: Route preview result.
    """
    prompt: str = args or "<task>"
    result = ComxTuiCommandResult(
        command=command_name,
        title="route preview",
        body=f"Use `comx-agent route recommend --task {prompt!r}` for typed routing.",
    )
    return result


def _routed_mcp_args(handler_key: str, args: str) -> str:
    """Normalize MCP slash-command variants into `/mcp` panel args.

    Args:
        handler_key [str]: Slash command handler key.
        args [str]: Inline slash-command args.

    Returns:
        str: MCP panel args.
    """
    if handler_key == "mcp_servers":
        routed_args = ""
    elif handler_key == "mcp_tools":
        routed_args = f"tools {args}"
    elif handler_key == "mcp_call":
        routed_args = f"call {args}"
    else:
        routed_args = args
    return routed_args


def _session_result(
    command_name: str,
    workspace: Path,
    current_session: ComxTuiSessionRecord | None,
) -> ComxTuiCommandResult:
    """Build a TUI session result.

    Args:
        command_name [str]: Slash command name.
        workspace [Path]: Workspace root.
        current_session [ComxTuiSessionRecord | None]: Optional active session.

    Returns:
        ComxTuiCommandResult: Session result.
    """
    if current_session is None:
        body = (
            "Current session details are available inside the interactive TUI loop.\n"
            f"Use `comx-agent sessions show <session-id> --cwd {workspace}` "
            "to inspect persisted session records."
        )
    else:
        body = (
            f"session={current_session.session_id} "
            f"status={current_session.status} "
            f"commands={len(current_session.command_history)}"
        )
    result = ComxTuiCommandResult(
        command=command_name,
        title="session",
        body=body,
    )
    return result


def _next_result(
    command_name: str,
    next_action: NextActionResult | None,
) -> ComxTuiCommandResult:
    """Build a next-action result.

    Args:
        command_name [str]: Slash command name.
        next_action [NextActionResult | None]: Optional next action.

    Returns:
        ComxTuiCommandResult: Next-action result.
    """
    body = "Next action has not been loaded."
    if next_action is not None:
        body = next_action.summary
    result = ComxTuiCommandResult(command=command_name, title="next action", body=body)
    return result


def _team_result(command_name: str) -> ComxTuiCommandResult:
    """Build a read-only Team panel result.

    Args:
        command_name [str]: Slash command name.

    Returns:
        ComxTuiCommandResult: Team panel result.
    """
    result = ComxTuiCommandResult(
        command=command_name,
        title="Team panel",
        body=(
            "Team state is read-only from this TUI route.\n"
            "Use `omx team status <team> --json` for live worker/task/pane evidence, "
            "or `comx-agent team --help` for adapter-owned typed Team commands."
        ),
    )
    return result


def _ultragoal_result(command_name: str, workspace: Path) -> ComxTuiCommandResult:
    """Build a read-only UltraGoal panel result.

    Args:
        command_name [str]: Slash command name.
        workspace [Path]: Workspace root.

    Returns:
        ComxTuiCommandResult: UltraGoal panel result.
    """
    goals_path: Path = workspace / ".omx" / "ultragoal" / "goals.json"
    ledger_path: Path = workspace / ".omx" / "ultragoal" / "ledger.jsonl"
    body = "\n".join(
        (
            f"goals: {goals_path}",
            f"ledger: {ledger_path}",
            f"goals_exists: {goals_path.exists()}",
            f"ledger_exists: {ledger_path.exists()}",
            "Use `omx ultragoal complete-goals --json` and checkpoint commands for mutations.",
        )
    )
    result = ComxTuiCommandResult(
        command=command_name,
        title="UltraGoal panel",
        body=body,
    )
    return result


def _goal_result(command_name: str) -> ComxTuiCommandResult:
    """Build a Codex goal panel result.

    Args:
        command_name [str]: Slash command name.

    Returns:
        ComxTuiCommandResult: Codex goal panel result.
    """
    result = ComxTuiCommandResult(
        command=command_name,
        title="Codex goal panel",
        body=(
            "Codex goal state is owned by the active Codex session.\n"
            "Use Codex `/goal` or the adapter `comx-agent goal --help` surfaces for explicit goal lifecycle commands."
        ),
    )
    return result


def _research_result(
    command_name: str,
    workspace: Path,
    args: str,
) -> ComxTuiCommandResult:
    """Build a research/interview workflow planning result.

    Args:
        command_name [str]: Slash command name.
        workspace [Path]: Workspace root.
        args [str]: Inline objective text.

    Returns:
        ComxTuiCommandResult: Research workflow plan result.
    """
    objective: str = args or "Clarify and research the current task."
    research_plan: ComxResearchWorkflowPlan = create_research_workflow_plan(
        workspace,
        objective,
        include_team=True,
        include_alexandria=True,
    )
    result = ComxTuiCommandResult(
        command=command_name,
        title="research workflow plan",
        body=(
            f"research_id: {research_plan.research_id}\n"
            f"objective: {research_plan.objective}\n"
            f"artifact: {research_plan.artifact_path}\n"
            "status: planned; no external research tools executed"
        ),
        read_only=False,
        artifact_path=research_plan.artifact_path,
        warnings=research_plan.warnings,
    )
    return result


def route_tui_slash_command(
    command_text: str,
    cwd: str | Path,
    next_action: NextActionResult | None = None,
    current_session: ComxTuiSessionRecord | None = None,
) -> ComxTuiCommandResult:
    """Route one normalized TUI slash command.

    Args:
        command_text [str]: Normalized command text.
        cwd [str | Path]: Workspace root.
        next_action [NextActionResult | None]: Optional next action.
        current_session [ComxTuiSessionRecord | None]: Optional active TUI session.

    Returns:
        ComxTuiCommandResult: Command result.
    """
    command: ComxTuiSlashCommand | None = find_tui_slash_command(command_text)
    if command is None:
        raise ValueError(f"unknown slash command: {command_text}")

    workspace = Path(cwd)
    args: str = get_tui_slash_command_args(command_text)
    if command.handler_key == "help":
        result = ComxTuiCommandResult(
            command=command.name,
            title="slash command help",
            body=format_tui_slash_command_help(),
        )
        return result
    if command.handler_key == "status":
        return _status_result(workspace, next_action)
    if command.handler_key == "surface":
        return _surface_result(command.name, workspace)
    if command.handler_key == "commands":
        return build_tui_commands_result(command.name, workspace)
    if command.handler_key == "run":
        return build_tui_recipe_preview_result(command.name, workspace, args)
    if command.handler_key == "route":
        return _route_result(command.name, args)
    if command.handler_key in {"mcp", "mcp_servers", "mcp_tools", "mcp_call"}:
        routed_args: str = _routed_mcp_args(command.handler_key, args)
        return build_tui_mcp_result(workspace, routed_args)
    if command.handler_key == "sessions":
        result = ComxTuiCommandResult(
            command=command.name,
            title="sessions",
            body=f"Use `comx-agent sessions list --cwd {workspace}` to inspect durable TUI sessions.",
        )
        return result
    if command.handler_key == "session":
        return _session_result(command.name, workspace, current_session)
    if command.handler_key == "next":
        return _next_result(command.name, next_action)
    if command.handler_key == "team":
        return _team_result(command.name)
    if command.handler_key == "ultragoal":
        return _ultragoal_result(command.name, workspace)
    if command.handler_key == "goal":
        return _goal_result(command.name)
    if command.handler_key in {"research", "interview"}:
        return _research_result(command.name, workspace, args)

    raise ValueError(f"No TUI handler is implemented for {command.name}.")
