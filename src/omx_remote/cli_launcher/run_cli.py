from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.commands.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.command_recipe_loader import CommandRecipeLoadError
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandExecutionPlan,
    CommandRecipe,
)


def _format_error_payload(error: Exception) -> str:
    """Format one run CLI error as JSON.

    Args:
        error [Exception]: Error to render.

    Returns:
        str: JSON error payload.
    """
    payload: dict[str, object] = {"ok": False, "error": str(error)}
    error_payload: str = orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
    return error_payload


def _format_plan_human(plan: CommandExecutionPlan) -> str:
    """Format a command plan for humans.

    Args:
        plan [CommandExecutionPlan]: Plan to render.

    Returns:
        str: Human-readable plan summary.
    """
    lines: list[str] = [
        f"command: {plan.qualified_id}",
        f"dry_run: {plan.dry_run}",
        f"risk: {plan.risk}",
    ]
    lines.extend(f"step {step.index}: {' '.join(step.native_argv)}" for step in plan.steps)
    lines.extend(f"blocker: {blocker}" for blocker in plan.blocked_reasons)
    plan_text: str = "\n".join(lines)
    return plan_text


def run_command(
    command_id: str | None = typer.Argument(
        None,
        help="Qualified or unambiguous command id. Omit for one-off prompt dry-run.",
    ),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve config, prompts, and artifacts.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command config path override, relative to --cwd when not absolute.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Only build and print the execution plan. Required in this slice.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Provider for one-off prompt dry-run, currently codex.",
    ),
    prompt_file: Path | None = typer.Option(
        None,
        "--prompt-file",
        help="Prompt file for one-off prompt dry-run.",
    ),
    inline_prompt: str | None = typer.Option(
        None,
        "--inline-prompt",
        help="Inline prompt for one-off prompt dry-run.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the command plan as JSON.",
    ),
) -> None:
    """Dry-run a project-owned command recipe or one-off prompt.

    Args:
        command_id [str | None]: Qualified or unambiguous command id.
        cwd [Path]: Repository root used for path resolution.
        config_path [Path | None]: Optional config path override.
        dry_run [bool]: Whether to only print a plan.
        provider [str | None]: One-off prompt provider.
        prompt_file [Path | None]: Optional one-off prompt file.
        inline_prompt [str | None]: Optional one-off inline prompt.
        json_output [bool]: Whether to print JSON.
    """
    try:
        if not dry_run:
            raise ValueError("Only --dry-run planning is supported in this slice.")

        if command_id is None:
            selected_provider: str = "codex" if provider is None else provider
            recipe: CommandRecipe = build_one_off_prompt_recipe(
                provider=selected_provider,
                prompt_file=prompt_file,
                inline_prompt=inline_prompt,
            )
        else:
            catalog: CommandCatalog = load_command_catalog(
                cwd=cwd,
                config_path=config_path,
            )
            recipe = resolve_command_recipe(catalog, command_id)

        plan: CommandExecutionPlan = build_command_execution_plan(
            recipe,
            cwd=cwd,
            dry_run=True,
        )
    except (
        CommandCatalogResolutionError,
        CommandRecipeLoadError,
        ValidationError,
        ValueError,
    ) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(plan.model_dump_json(indent=2))
        return

    typer.echo(_format_plan_human(plan))
