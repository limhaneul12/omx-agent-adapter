from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.commands.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.command_executor import CommandExecutor
from omx_remote.runtime.commands.command_recipe_loader import CommandRecipeLoadError
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
)
from omx_remote.runtime.runs.run_record_writer import write_dry_run_record
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandActualRunResult,
    CommandActualRunStatus,
    CommandAutonomyMode,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandExecutionPlan,
    CommandRecipe,
)
from omx_remote.schemas.runs.run_record_schemas import (
    RunCommandRecordResult,
    RunRecord,
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
    lines.extend(
        f"step {step.index}: {' '.join(step.native_argv)}" for step in plan.steps
    )
    lines.extend(f"blocker: {blocker}" for blocker in plan.blocked_reasons)
    plan_text: str = "\n".join(lines)
    return plan_text


def _format_actual_human(result: CommandActualRunResult) -> str:
    """Format an actual command result for humans.

    Args:
        result [CommandActualRunResult]: Actual run result.

    Returns:
        str: Human-readable execution summary.
    """
    lines: list[str] = [
        f"command: {result.qualified_id}",
        f"status: {result.status}",
        f"run_id: {result.run_id}",
        f"result: {result.result_path}",
    ]
    lines.extend(
        f"step {step.index}: {step.command} {step.status}" for step in result.steps
    )
    actual_text: str = "\n".join(lines)
    return actual_text


def _actual_run_exit_code(status: CommandActualRunStatus) -> int:
    """Return the shell exit code for one actual execution status.

    Args:
        status: See function signature.

    Returns:
        See function return annotation."""
    if status == CommandActualRunStatus.SUCCEEDED:
        return 0
    if status == CommandActualRunStatus.FAILED:
        return 1
    if status == CommandActualRunStatus.BLOCKED:
        return 2
    return 3


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
        help="Only build and print the execution plan.",
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Execute the planned command through the agent autonomy pipeline.",
    ),
    autonomy: str | None = typer.Option(
        None,
        "--autonomy",
        help="Required autonomy mode for --execute. Currently: agent.",
    ),
    task: str | None = typer.Option(
        None,
        "--task",
        help="Optional task text used to fill recipe placeholders such as <task>.",
    ),
    timeout_sec: float = typer.Option(
        120.0,
        "--timeout-sec",
        help="Per-step subprocess timeout for actual execution.",
    ),
    max_attempts: int = typer.Option(
        2,
        "--max-attempts",
        help="Maximum attempts for retryable actual execution steps.",
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
    record_run: bool = typer.Option(
        False,
        "--record-run",
        help="Write a dry-run record under .agent-remote/runs. Actual execution always records.",
    ),
) -> None:
    """Dry-run or execute a project-owned command recipe or one-off prompt.

    Args:
        command_id [str | None]: Qualified or unambiguous command id.
        cwd [Path]: Repository root used for path resolution.
        config_path [Path | None]: Optional config path override.
        dry_run [bool]: Whether to only print a plan.
        execute [bool]: Whether to execute the plan.
        autonomy [str | None]: Explicit autonomy mode for actual execution.
        task [str | None]: Optional task text for placeholder substitution.
        timeout_sec [float]: Per-step subprocess timeout.
        max_attempts [int]: Maximum attempts for retryable steps.
        provider [str | None]: One-off prompt provider.
        prompt_file [Path | None]: Optional one-off prompt file.
        inline_prompt [str | None]: Optional one-off inline prompt.
        json_output [bool]: Whether to print JSON.
        record_run [bool]: Whether to write a run record.
    """
    run_record: RunRecord | None = None
    try:
        if dry_run and execute:
            raise ValueError("Pass only one of --dry-run or --execute.")
        if not dry_run and not execute:
            raise ValueError(
                "Pass --dry-run to preview or --execute to run the command."
            )
        if execute and autonomy is None:
            raise ValueError("--execute requires explicit --autonomy agent.")

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
            dry_run=dry_run,
        )
        if dry_run and record_run:
            run_record = write_dry_run_record(plan, cwd=cwd)
        if execute:
            autonomy_mode = CommandAutonomyMode(autonomy)
            executor = CommandExecutor(
                max_attempts=max_attempts, timeout_seconds=timeout_sec
            )
            actual_result: CommandActualRunResult = executor.execute(
                plan,
                cwd=cwd,
                autonomy_mode=autonomy_mode,
                task_text=task,
            )
            if json_output:
                typer.echo(actual_result.model_dump_json(indent=2))
                exit_code = _actual_run_exit_code(actual_result.status)
                if exit_code != 0:
                    raise typer.Exit(code=exit_code)
                return
            typer.echo(_format_actual_human(actual_result))
            exit_code = _actual_run_exit_code(actual_result.status)
            if exit_code != 0:
                raise typer.Exit(code=exit_code)
            return
    except (
        CommandCatalogResolutionError,
        CommandRecipeLoadError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        if run_record is not None:
            result = RunCommandRecordResult(plan=plan, run_record=run_record)
            typer.echo(result.model_dump_json(indent=2))
            return
        typer.echo(plan.model_dump_json(indent=2))
        return

    output_text: str = _format_plan_human(plan)
    if run_record is not None:
        output_text = f"{output_text}\nrecorded_run: {run_record.run_id}"
    typer.echo(output_text)
