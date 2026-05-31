from pathlib import Path

from omx_remote.runtime.commands.command_catalog_resolver import (
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandExecutionPlan,
    CommandPlanStep,
    CommandRecipe,
)


def _format_run_plan_step(step: CommandPlanStep) -> tuple[str, ...]:
    """Render one command dry-run step for the TUI.

    Args:
        step [CommandPlanStep]: Planned command step.

    Returns:
        tuple[str, ...]: Human-readable lines for the step.
    """
    lines: list[str] = [f"step {step.index}: {' '.join(step.native_argv)}"]
    if step.inline_prompt is not None:
        prompt_preview: str = step.inline_prompt.replace("\n", " ")[:320]
        lines.append(f"  prompt: {prompt_preview}")
    if step.role_lanes:
        role_text: str = ", ".join(
            f"{lane.id}:{lane.execution}" for lane in step.role_lanes
        )
        lines.append(f"  roles: {role_text}")
    if step.expected_artifacts:
        artifacts_text: str = ", ".join(step.expected_artifacts)
        lines.append(f"  artifacts: {artifacts_text}")
    lines.extend(f"  blocker: {blocker}" for blocker in step.blocked_reasons)
    step_lines: tuple[str, ...] = tuple(lines)
    return step_lines


def format_tui_run_plan(plan: CommandExecutionPlan) -> str:
    """Render an inspectable command dry-run plan for the TUI.

    Args:
        plan [CommandExecutionPlan]: Typed dry-run plan.

    Returns:
        str: Human-readable dry-run plan body.
    """
    lines: list[str] = [
        f"command: {plan.qualified_id}",
        "dry_run: true",
        f"risk: {plan.risk}",
    ]
    for step in plan.steps:
        lines.extend(_format_run_plan_step(step))
    lines.extend(f"blocker: {blocker}" for blocker in plan.blocked_reasons)
    lines.append("No command recipe was executed from the TUI.")
    run_plan_text: str = "\n".join(lines)
    return run_plan_text


def build_tui_run_plan_preview(
    recipe_id: str,
    cwd: str | Path,
    task_text: str | None = None,
) -> str:
    """Build a typed command recipe preview body for the TUI.

    Args:
        recipe_id [str]: Qualified or unambiguous command recipe id.
        cwd [str | Path]: Workspace root.
        task_text [str | None]: Optional task prompt for preview rendering.

    Returns:
        str: Human-readable typed dry-run preview.
    """
    catalog: CommandCatalog = load_command_catalog(cwd=cwd)
    recipe: CommandRecipe = resolve_command_recipe(catalog, recipe_id)
    plan: CommandExecutionPlan = build_command_execution_plan(
        recipe,
        cwd=cwd,
        dry_run=True,
        task_text=task_text,
    )
    preview_text: str = format_tui_run_plan(plan)
    return preview_text
