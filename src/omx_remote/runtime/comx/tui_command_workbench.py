import shlex
from pathlib import Path

from omx_remote.runtime.commands.planning.command_runtime_options import (
    build_command_runtime_options,
)
from omx_remote.runtime.comx.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.runtime.comx.tui_command_sections import command_section_label
from omx_remote.runtime.comx.tui_run_plan_preview import build_tui_run_plan_preview
from omx_remote.schemas.comx.control_surface_schemas import ComxControlSurfaceInventory
from omx_remote.schemas.comx.tui_schemas import (
    ComxTuiCommandResult,
    ComxTuiRunPreviewArgs,
)

_VALUE_OPTIONS: frozenset[str] = frozenset({"--task", "--model", "--reasoning-effort"})
_FLAG_OPTIONS: frozenset[str] = frozenset({"--xhigh", "--madmax"})


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


def _split_run_preview_tokens(args: str) -> tuple[list[str], str | None]:
    """Split `/run` args into shell tokens and optional `::` task fallback.

    Args:
        args [str]: Inline arguments after `/run`.

    Returns:
        tuple[list[str], str | None]: Parsed tokens and optional task fallback.
    """
    task_fallback: str | None = None
    parse_source = args
    if "::" in args:
        left_side, right_side = args.split("::", maxsplit=1)
        parse_source = left_side.strip()
        task_fallback = right_side.strip() or None
    try:
        tokens = shlex.split(parse_source)
    except ValueError:
        tokens = parse_source.split()
    return tokens, task_fallback


def _read_option_values(
    tokens: list[str],
    start_index: int,
) -> tuple[str, int]:
    """Read a value option that may span unquoted words until the next option.

    Args:
        tokens [list[str]]: Parsed `/run` tokens.
        start_index [int]: Index immediately after the option token.

    Returns:
        tuple[str, int]: Option value and next unread token index.
    """
    if start_index >= len(tokens) or tokens[start_index].startswith("--"):
        raise ValueError(f"{tokens[start_index - 1]} requires a value.")
    value_tokens: list[str] = []
    index = start_index
    while index < len(tokens) and not tokens[index].startswith("--"):
        value_tokens.append(tokens[index])
        index += 1
    value = " ".join(value_tokens)
    return value, index


def _parse_long_option_token(
    token: str,
) -> tuple[str, str | None]:
    """Split `--name=value` tokens while preserving regular option tokens.

    Args:
        token [str]: Candidate option token.

    Returns:
        tuple[str, str | None]: Option name and inline value.
    """
    if "=" not in token:
        parsed = (token, None)
        return parsed
    option_name, option_value = token.split("=", maxsplit=1)
    parsed = (option_name, option_value)
    return parsed


def _parse_run_preview_args(args: str) -> ComxTuiRunPreviewArgs:
    """Parse `/run` preview args into recipe id and optional task prompt.

    Args:
        args [str]: Inline arguments after `/run`.

    Returns:
        ComxTuiRunPreviewArgs: Parsed recipe id, task text, and runtime options.
    """
    tokens, task_fallback = _split_run_preview_tokens(args=args)
    if not tokens:
        raise ValueError("/run requires a command recipe id.")

    command_tokens: list[str] = []
    task_text: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    xhigh = False
    madmax = False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--"):
            option_name, inline_value = _parse_long_option_token(token=token)
            if option_name not in _VALUE_OPTIONS and option_name not in _FLAG_OPTIONS:
                raise ValueError(f"unsupported /run option: {option_name}")
            if option_name in _FLAG_OPTIONS:
                if inline_value is not None:
                    raise ValueError(f"{option_name} does not accept a value.")
                if option_name == "--xhigh":
                    xhigh = True
                else:
                    madmax = True
                index += 1
                continue
            if inline_value is None:
                value, index = _read_option_values(
                    tokens=tokens,
                    start_index=index + 1,
                )
            else:
                value = inline_value
                index += 1
            if option_name == "--task":
                task_text = value
            elif option_name == "--model":
                model = value
            else:
                reasoning_effort = value
            continue
        command_tokens.append(token)
        index += 1
    recipe_id = " ".join(command_tokens).strip()
    if not recipe_id:
        raise ValueError("/run requires a command recipe id.")
    effective_task = task_text if task_text is not None else task_fallback
    runtime_options = build_command_runtime_options(
        model=model,
        reasoning_effort=reasoning_effort,
        xhigh=xhigh,
        madmax=madmax,
    )

    parsed_args = ComxTuiRunPreviewArgs(
        recipe_id=recipe_id,
        task_text=effective_task,
        runtime_options=runtime_options,
    )
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
    preview_args = _parse_run_preview_args(args=args)
    result = ComxTuiCommandResult(
        command=command_name,
        title="command recipe preview",
        body=build_tui_run_plan_preview(
            recipe_id=preview_args.recipe_id,
            cwd=workspace,
            task_text=preview_args.task_text,
            runtime_options=preview_args.runtime_options,
        ),
        warnings=("No command recipe was executed from the TUI.",),
    )
    return result
