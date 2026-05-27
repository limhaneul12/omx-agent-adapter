import asyncio
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
from omx_remote.runtime.comx.tui_run_plan_preview import build_tui_run_plan_preview
from omx_remote.runtime.mcp.mcp_registry_reader import (
    read_mcp_servers,
    resolve_mcp_server,
)
from omx_remote.runtime.mcp.mcp_tool_client import list_mcp_tools
from omx_remote.schemas.comx.control_surface_schemas import ComxControlSurfaceInventory
from omx_remote.schemas.comx.research_workflow_schemas import ComxResearchWorkflowPlan
from omx_remote.schemas.comx.session_schemas import ComxTuiSessionRecord
from omx_remote.schemas.comx.tui_schemas import (
    ComxTuiCommandResult,
    ComxTuiSlashCommand,
)
from omx_remote.schemas.mcp.client_schemas import (
    McpServerConfig,
    McpServerListResult,
    McpToolListResult,
    McpTransportKind,
)
from omx_remote.schemas.next.next_action_schemas import NextActionResult

SECRET_ARGUMENT_TERMS: tuple[str, ...] = (
    "auth",
    "bearer",
    "credential",
    "header",
    "key",
    "password",
    "secret",
    "token",
)
SECRET_ARGUMENT_FLAGS: frozenset[str] = frozenset(
    {
        "-H",
        "--header",
        "--headers",
        "--authorization",
    }
)


def _strip_url_query(value: str) -> str:
    """Remove query strings from URL-like display values.

    Args:
        value [str]: Candidate display value.

    Returns:
        str: Value with URL query removed.
    """
    if "://" not in value or "?" not in value:
        return value
    redacted_value: str = value.split("?", 1)[0]
    return redacted_value


def _secret_argument_name(value: str) -> bool:
    """Check whether a CLI argument name appears secret-bearing.

    Args:
        value [str]: Argument name or key.

    Returns:
        bool: True when the name is secret-like.
    """
    normalized_value: str = value.strip().lstrip("-").lower().replace("_", "-")
    secret_like: bool = value in SECRET_ARGUMENT_FLAGS or any(
        term in normalized_value for term in SECRET_ARGUMENT_TERMS
    )
    return secret_like


def _redact_argument_value(value: str) -> str:
    """Redact secret-looking CLI argument values while preserving shape.

    Args:
        value [str]: CLI argument value.

    Returns:
        str: Redacted display value.
    """
    if "=" in value:
        key, _ = value.split("=", 1)
        if _secret_argument_name(key):
            return f"{key}=<redacted>"
    if ":" in value:
        key, _ = value.split(":", 1)
        if _secret_argument_name(key):
            return f"{key}:<redacted>"
    return _strip_url_query(value)


def _redacted_stdio_target(command: str, args: tuple[str, ...]) -> str:
    """Render a stdio MCP target without leaking secret-like args.

    Args:
        command [str]: Stdio command.
        args [tuple[str, ...]]: Stdio command args.

    Returns:
        str: Safe target display string.
    """
    rendered_parts: list[str] = [command]
    redact_next = False
    for arg in args:
        if redact_next:
            rendered_parts.append("<redacted>")
            redact_next = False
            continue
        rendered_arg: str = _redact_argument_value(arg)
        rendered_parts.append(rendered_arg)
        if rendered_arg == arg and _secret_argument_name(arg):
            redact_next = True

    rendered_target: str = " ".join(rendered_parts)
    return rendered_target


def _redacted_target(server: McpServerConfig) -> str:
    """Render a safe MCP target string.

    Args:
        server [McpServerConfig]: MCP server.

    Returns:
        str: Redacted target string.
    """
    if server.transport.type == McpTransportKind.STREAMABLE_HTTP:
        if server.transport.url is None:
            return "-"
        url_without_query: str = _strip_url_query(server.transport.url)
        return url_without_query

    if server.transport.command is not None:
        return _redacted_stdio_target(
            server.transport.command,
            server.transport.args,
        )
    return "-"


def _format_mcp_server_rows(registry: McpServerListResult) -> str:
    """Render MCP server rows for a TUI command result.

    Args:
        registry [McpServerListResult]: MCP registry.

    Returns:
        str: Human-readable rows.
    """
    if not registry.servers:
        return (
            "No MCP servers discovered. Use `comx-agent mcp add ...` to register one."
        )

    lines: list[str] = [
        "source  name                         enabled  auth          transport          target",
    ]
    for server in registry.servers:
        enabled_label: str = "yes" if server.enabled else "no"
        auth_label: str = server.auth_status or "n/a"
        lines.append(
            f"{server.source:<6}  {server.qualified_name:<27}  "
            f"{enabled_label:<7}  {auth_label:<12}  {server.transport.type:<17}  "
            f"{_redacted_target(server)}"
        )
        if server.disabled_reason is not None:
            lines.append(f"  disabled_reason: {server.disabled_reason}")
    lines.extend(f"warning: {warning}" for warning in registry.warnings)
    return "\n".join(lines)


def _format_tool_rows(result: McpToolListResult) -> str:
    """Render MCP tool rows.

    Args:
        result [McpToolListResult]: Tool list result.

    Returns:
        str: Human-readable rows.
    """
    if not result.tools:
        return f"No tools advertised by {result.server.qualified_name}."

    lines: list[str] = [f"tools for {result.server.qualified_name}:"]
    for tool in result.tools:
        description: str = tool.description or tool.title or "-"
        lines.append(f"- {tool.name}: {description}")
    lines.extend(f"warning: {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _format_command_inventory(inventory: ComxControlSurfaceInventory) -> str:
    """Render composed command recipes.

    Args:
        inventory [ComxControlSurfaceInventory]: Surface inventory.

    Returns:
        str: Human-readable command list.
    """
    if not inventory.composed_commands:
        return "No composed command recipes are available."

    lines: list[str] = ["composed commands:"]
    lines.extend(
        f"- {command.qualified_id} [{command.risk}] steps={command.step_count}: "
        f"{command.description}"
        for command in inventory.composed_commands
    )
    return "\n".join(lines)


def _status_result(
    cwd: Path, next_action: NextActionResult | None
) -> ComxTuiCommandResult:
    """Build a status result.

    Args:
        cwd [Path]: Workspace root.
        next_action [NextActionResult | None]: Optional next action.
        current_session [ComxTuiSessionRecord | None]: Optional active TUI session.

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
    return ComxTuiCommandResult(
        command="/status",
        title="comx-agent status",
        body=body,
        warnings=registry.warnings,
    )


def _mcp_result(cwd: Path, args: str) -> ComxTuiCommandResult:
    """Build an MCP command result.

    Args:
        cwd [Path]: Workspace root.
        args [str]: Inline args after /mcp.

    Returns:
        ComxTuiCommandResult: Result.
    """
    normalized_args: str = args.strip()
    if normalized_args.startswith("tools "):
        server_name: str = normalized_args.removeprefix("tools ").strip()
        if not server_name:
            raise ValueError("/mcp tools requires a server name.")
        registry: McpServerListResult = read_mcp_servers(cwd=cwd)
        server: McpServerConfig = resolve_mcp_server(registry.servers, server_name)
        try:
            tool_result: McpToolListResult = asyncio.run(list_mcp_tools(server))
        except Exception as error:
            return ComxTuiCommandResult(
                command="/mcp tools",
                title=f"MCP tools error: {server.qualified_name}",
                body=f"Could not list tools for {server.qualified_name}: {error}",
                warnings=(
                    "MCP tool listing may start an external stdio process or open a network connection.",
                    *registry.warnings,
                ),
            )
        return ComxTuiCommandResult(
            command="/mcp tools",
            title=f"MCP tools: {server.qualified_name}",
            body=_format_tool_rows(tool_result),
            warnings=(*registry.warnings, *tool_result.warnings),
        )

    if normalized_args.startswith("call "):
        call_parts: list[str] = normalized_args.removeprefix("call ").split()
        if len(call_parts) < 2:
            raise ValueError("/mcp call requires <server> <tool>.")
        registry = read_mcp_servers(cwd=cwd)
        server = resolve_mcp_server(registry.servers, call_parts[0])
        body = "\n".join(
            (
                f"dry_run: {server.qualified_name}.{call_parts[1]} not executed",
                "Use `comx-agent mcp call ... --execute` outside the TUI for explicit execution.",
            )
        )
        return ComxTuiCommandResult(
            command="/mcp call",
            title="MCP tool call preview",
            body=body,
            warnings=("Dry-run only. No MCP tool was executed.", *registry.warnings),
        )

    registry = read_mcp_servers(cwd=cwd)
    title: str = "MCP servers"
    if normalized_args == "verbose":
        title = "MCP servers (verbose, redacted)"
    return ComxTuiCommandResult(
        command="/mcp",
        title=title,
        body=_format_mcp_server_rows(registry),
        warnings=registry.warnings,
    )


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
        return ComxTuiCommandResult(
            command=command.name,
            title="slash command help",
            body=format_tui_slash_command_help(),
        )
    if command.handler_key == "status":
        return _status_result(workspace, next_action)
    if command.handler_key == "surface":
        inventory = build_comx_control_surface_inventory(cwd=workspace)
        return ComxTuiCommandResult(
            command=command.name,
            title="control surface",
            body=(
                f"native={inventory.native_count} composed={inventory.composed_count}\n"
                "Use /commands to inspect composed recipes."
            ),
        )
    if command.handler_key == "commands":
        inventory = build_comx_control_surface_inventory(cwd=workspace)
        return ComxTuiCommandResult(
            command=command.name,
            title="composed commands",
            body=_format_command_inventory(inventory),
        )
    if command.handler_key == "run":
        recipe_id: str = args.strip()
        if not recipe_id:
            raise ValueError("/run requires a command recipe id.")
        return ComxTuiCommandResult(
            command=command.name,
            title="command recipe preview",
            body=build_tui_run_plan_preview(recipe_id, workspace),
            warnings=("No command recipe was executed from the TUI.",),
        )
    if command.handler_key == "route":
        prompt: str = args or "<task>"
        return ComxTuiCommandResult(
            command=command.name,
            title="route preview",
            body=f"Use `comx-agent route recommend --task {prompt!r}` for typed routing.",
        )
    if command.handler_key in {"mcp", "mcp_servers", "mcp_tools", "mcp_call"}:
        routed_args: str = args
        if command.handler_key == "mcp_servers":
            routed_args = ""
        if command.handler_key == "mcp_tools":
            routed_args = f"tools {args}"
        if command.handler_key == "mcp_call":
            routed_args = f"call {args}"
        return _mcp_result(workspace, routed_args)
    if command.handler_key == "sessions":
        return ComxTuiCommandResult(
            command=command.name,
            title="sessions",
            body=f"Use `comx-agent sessions list --cwd {workspace}` to inspect durable TUI sessions.",
        )
    if command.handler_key == "session":
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
        return ComxTuiCommandResult(
            command=command.name,
            title="session",
            body=body,
        )
    if command.handler_key == "next":
        body = "Next action has not been loaded."
        if next_action is not None:
            body = next_action.summary
        return ComxTuiCommandResult(
            command=command.name, title="next action", body=body
        )
    if command.handler_key == "team":
        return ComxTuiCommandResult(
            command=command.name,
            title="Team panel",
            body=(
                "Team state is read-only from this TUI route.\n"
                "Use `omx team status <team> --json` for live worker/task/pane evidence, "
                "or `comx-agent team --help` for adapter-owned typed Team commands."
            ),
        )
    if command.handler_key == "ultragoal":
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
        return ComxTuiCommandResult(
            command=command.name,
            title="UltraGoal panel",
            body=body,
        )
    if command.handler_key == "goal":
        return ComxTuiCommandResult(
            command=command.name,
            title="Codex goal panel",
            body=(
                "Codex goal state is owned by the active Codex session.\n"
                "Use Codex `/goal` or the adapter `comx-agent goal --help` surfaces for explicit goal lifecycle commands."
            ),
        )
    if command.handler_key in {"research", "interview"}:
        objective: str = args or "Clarify and research the current task."
        research_plan: ComxResearchWorkflowPlan = create_research_workflow_plan(
            workspace,
            objective,
            include_team=True,
            include_alexandria=True,
        )
        return ComxTuiCommandResult(
            command=command.name,
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

    raise ValueError(f"No TUI handler is implemented for {command.name}.")
