import os
from pathlib import Path

from omx_remote.runtime.comx.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.runtime.comx.tui_command_catalog import list_tui_slash_commands
from omx_remote.runtime.mcp.mcp_registry_reader import read_mcp_servers
from omx_remote.schemas.comx.control_surface_schemas import ComxControlSurfaceInventory
from omx_remote.schemas.comx.tui_schemas import ComxTuiSnapshot, ComxTuiStatusLine
from omx_remote.schemas.mcp.client_schemas import McpServerListResult
from omx_remote.schemas.next.next_action_schemas import NextActionResult


def _permission_label() -> str:
    """Infer a concise permission label from environment hints.

    Returns:
        str: Permission label for the TUI header.
    """
    bypass_value: str | None = os.environ.get("CODEX_SANDBOX") or os.environ.get(
        "OMX_PERMISSIONS"
    )
    if bypass_value is not None and bypass_value.lower() in {"yolo", "danger-full-access"}:
        permission_label: str = "YOLO mode"
        return permission_label

    permission_label = "guarded"
    return permission_label


def build_tui_snapshot(
    cwd: str | Path,
    next_action: NextActionResult | None = None,
    prompt: str | None = None,
) -> ComxTuiSnapshot:
    """Build one read-only TUI frame snapshot.

    Args:
        cwd [str | Path]: Workspace root.
        next_action [NextActionResult | None]: Optional next-action evidence.
        prompt [str | None]: Optional prompt line to display.

    Returns:
        ComxTuiSnapshot: Typed TUI frame data.
    """
    cwd_path: Path = Path(cwd)
    workspace: str = str(cwd_path.resolve())
    runtime_label: str = "runtime: read-only"
    goal_label: str = "goal: idle"
    ralph_label: str = "Ralph idle"
    teams_label: str = "Teams 0/0"
    warning_items: list[str] = []
    if next_action is not None:
        runtime_label = next_action.recommended_action
        goal_label = "safe" if next_action.safe_to_mutate else "blocked"
        warning_items.extend(next_action.blocked_actions)

    inventory: ComxControlSurfaceInventory = build_comx_control_surface_inventory(cwd=cwd_path)
    mcp_server_count = 0
    try:
        registry: McpServerListResult = read_mcp_servers(cwd=cwd_path)
        mcp_server_count = len(registry.servers)
        warning_items.extend(registry.warnings)
    except ValueError as error:
        warning_items.append(str(error))

    warnings: tuple[str, ...] = tuple(warning_items)

    status_line = ComxTuiStatusLine(
        model_label=os.environ.get("COMX_AGENT_MODEL", "gpt-5.5 xhigh"),
        workspace=workspace,
        permission_label=_permission_label(),
        runtime_label=runtime_label,
        goal_label=goal_label,
        ralph_label=ralph_label,
        teams_label=teams_label,
    )
    snapshot = ComxTuiSnapshot(
        title="COMX Agent",
        subtitle="Codex/OMX control surface",
        status_line=status_line,
        prompt=prompt or "Run /help for commands",
        tips=(
            "Use /status for the Codex/OMX cockpit snapshot.",
            "Use /surface and /commands to separate native support from recipes.",
            "Use /mcp to inspect MCP servers and /mcp tools <server> for tools.",
            "Use /research <objective> to create a staged evidence plan.",
        ),
        warnings=warnings,
        slash_command_count=len(list_tui_slash_commands()),
        mcp_server_count=mcp_server_count,
        composed_command_count=inventory.composed_count,
    )
    return snapshot


def render_tui_frame(snapshot: ComxTuiSnapshot) -> str:
    """Render one screenshot-style TUI frame.

    Args:
        snapshot [ComxTuiSnapshot]: TUI frame data.

    Returns:
        str: Terminal-renderable frame.
    """
    header_lines: tuple[str, ...] = (
        f">_  {snapshot.title}  ({snapshot.subtitle})",
        "",
        f"model:      {snapshot.status_line.model_label}   /model to change",
        f"workspace:  {snapshot.status_line.workspace}",
        f"permissions:{snapshot.status_line.permission_label}",
    )
    width: int = max(len(line) for line in header_lines) + 4
    border: str = "┌" + "─" * width + "┐"
    bottom: str = "└" + "─" * width + "┘"
    boxed_lines: list[str] = [border]
    boxed_lines.extend(f"│ {line.ljust(width - 2)} │" for line in header_lines)
    boxed_lines.append(bottom)

    body_lines: list[str] = [
        "",
        f"Tip: {snapshot.tips[0]}",
        "",
        "▣ Experimental runtime enabled: MCP client · UltraGoal orchestration · mixed Codex/OMX execution surfaces",
        "",
        f"> {snapshot.prompt}",
        "",
        (
            f"{snapshot.status_line.model_label} · "
            f"{snapshot.status_line.runtime_label} · "
            f"{snapshot.status_line.goal_label} · "
            f"{snapshot.status_line.ralph_label} · "
            f"{snapshot.status_line.teams_label}"
        ),
        (
            f"commands {snapshot.slash_command_count} · "
            f"recipes {snapshot.composed_command_count} · "
            f"mcp servers {snapshot.mcp_server_count}"
        ),
    ]
    body_lines.extend(f"warning: {warning}" for warning in snapshot.warnings)

    frame: str = "\n".join((*boxed_lines, *body_lines))
    return frame
