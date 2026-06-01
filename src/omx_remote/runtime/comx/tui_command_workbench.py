import shlex
from pathlib import Path

from omx_remote.runtime.comx.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.runtime.comx.tui_command_sections import command_section_label
from omx_remote.runtime.comx.tui_run_plan_preview import build_tui_run_plan_preview
from omx_remote.schemas.comx.control_surface_schemas import ComxControlSurfaceInventory
from omx_remote.schemas.comx.tui_schemas import ComxTuiCommandResult


def _format_command_inventory(inventory: ComxControlSurfaceInventory) -> str:
    """Render composed command recipes.

    Args:
        inventory [ComxControlSurfaceInventory]: Surface inventory.

    Returns:
        str: Human-readable command list.
    """
    if not inventory.composed_commands:
        return "No composed command recipes are available."

    grouped_commands: dict[str, list[str]] = {}
    ungrouped_lines: list[str] = []
    for command in inventory.composed_commands:
        section_label = command_section_label(command.id)
        quoted_command_id = shlex.quote(command.qualified_id)
        if section_label is None:
            ungrouped_lines.append(
                f"- {command.qualified_id} [{command.risk}] steps={command.step_count}: "
                f"{command.description}"
            )
            continue
        command_lines: list[str] = [
            (
                f"- {section_label.label} ({command.qualified_id}) "
                f"[{command.risk}] steps={command.step_count}: {command.description}"
            ),
            (
                "  dry_run: comx-agent run "
                f'{quoted_command_id} --cwd . --dry-run --task "<task>" --json'
            ),
            (
                "  execute_or_handoff: comx-agent run "
                f"{quoted_command_id} --cwd . --execute --autonomy agent "
                '--task "<task>" --json'
            ),
        ]
        if section_label.warning is not None:
            command_lines.append(f"  warning: {section_label.warning}")
        grouped_commands.setdefault(section_label.group, []).extend(command_lines)

    lines: list[str] = ["composed commands:"]
    for group_name in ("Lifecycle", "Macro", "Adapter Ops"):
        group_lines: list[str] | None = grouped_commands.get(group_name)
        if group_lines is None:
            continue
        lines.append(f"[{group_name}]")
        lines.extend(group_lines)
    if ungrouped_lines:
        lines.append("[Other]")
        lines.extend(ungrouped_lines)
    rendered_inventory: str = "\n".join(lines)
    return rendered_inventory


def _parse_run_preview_args(args: str) -> tuple[str, str | None]:
    """Parse `/run` preview args into recipe id and optional task prompt.

    Args:
        args [str]: Inline arguments after `/run`.

    Returns:
        tuple[str, str | None]: Recipe id and optional task text.
    """
    try:
        tokens: list[str] = shlex.split(args)
    except ValueError:
        tokens = args.split()
    if not tokens:
        raise ValueError("/run requires a command recipe id.")

    command_tokens: list[str] = tokens
    task_text: str | None = None
    if "--task" in tokens:
        task_index: int = tokens.index("--task")
        command_tokens = tokens[:task_index]
        task_tokens = tokens[task_index + 1 :]
        if task_tokens:
            task_text = " ".join(task_tokens)
    elif "::" in args:
        recipe_id, task_part = args.split("::", 1)
        recipe_id = recipe_id.strip()
        task_text = task_part.strip() or None
        parsed_args: tuple[str, str | None] = (recipe_id, task_text)
        return parsed_args

    recipe_id = " ".join(command_tokens).strip()
    if not recipe_id:
        raise ValueError("/run requires a command recipe id.")

    parsed_args: tuple[str, str | None] = (recipe_id, task_text)
    return parsed_args


def build_tui_commands_result(
    command_name: str, workspace: Path
) -> ComxTuiCommandResult:
    """Build the TUI composed-command workbench result.

    Args:
        command_name [str]: Slash command name.
        workspace [Path]: Workspace root.

    Returns:
        ComxTuiCommandResult: Command list result.
    """
    inventory: ComxControlSurfaceInventory = build_comx_control_surface_inventory(
        cwd=workspace
    )
    result = ComxTuiCommandResult(
        command=command_name,
        title="composed commands",
        body=_format_command_inventory(inventory),
    )
    return result


def build_tui_recipe_preview_result(
    command_name: str,
    workspace: Path,
    args: str,
) -> ComxTuiCommandResult:
    """Build a dry-run command recipe preview result.

    Args:
        command_name [str]: Slash command name.
        workspace [Path]: Workspace root.
        args [str]: Inline `/run` arguments.

    Returns:
        ComxTuiCommandResult: Command recipe preview result.
    """
    recipe_id, task_text = _parse_run_preview_args(args)
    result = ComxTuiCommandResult(
        command=command_name,
        title="command recipe preview",
        body=build_tui_run_plan_preview(recipe_id, workspace, task_text=task_text),
        warnings=("No command recipe was executed from the TUI.",),
    )
    return result
