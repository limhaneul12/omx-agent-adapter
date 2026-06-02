from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.runtime.commands.catalog.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.catalog.command_recipe_loader import (
    CommandRecipeLoadError,
)
from omx_remote.runtime.commands.execution.command_executor import CommandExecutor
from omx_remote.runtime.commands.planning.command_runtime_options import (
    build_command_runtime_options,
    runtime_options_summary_text,
)
from omx_remote.runtime.commands.planning.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
)
from omx_remote.runtime.company_run import engine as company_run_engine
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
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS,
    CompanyRunExecutionRequest,
    CompanyRunResult,
)
from omx_remote.schemas.run_record_schemas import (
    RunCommandRecordResult,
    RunRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunCouncilMode,
    CompanyRunTeamLaunchMode,
)


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
        f"runtime_options: {runtime_options_summary_text(plan.runtime_options)}",
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
        f"runtime_options: {runtime_options_summary_text(result.runtime_options)}",
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


def _company_run_exit_code(status: str) -> int:
    """Return shell exit code for a company-run result status.

    Args:
        status [str]: Company-run result status.

    Returns:
        int: Shell exit code.
    """
    if status == "succeeded":
        return 0
    if status == "failed":
        return 1
    if status == "blocked":
        return 2
    return 3


def _format_company_run_human(result: CompanyRunResult) -> str:
    """Format a company-run engine result for humans.

    Args:
        result [CompanyRunResult]: Company-run result to render.

    Returns:
        str: Human-readable result summary.
    """
    lines = [
        f"command: {result.qualified_id}",
        f"status: {result.status}",
        f"runtime_options: {runtime_options_summary_text(result.runtime_options)}",
        f"run_id: {result.run_id}",
        f"company_run_root: {result.company_run_root}",
        f"result: {result.result_path}",
    ]
    text = "\n".join(lines)
    return text


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
    timeout_sec: float | None = typer.Option(
        None,
        "--timeout-sec",
        help="Per-step subprocess timeout for actual execution. If omitted, command-specific defaults apply.",
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
        help="Write a dry-run record under .comx-agent/runs. Actual execution always records.",
    ),
    company_council_mode: str = typer.Option(
        CompanyRunCouncilMode.CODEX.value,
        "--council-mode",
        help="Company-run only: council/subagent execution mode, codex or artifact.",
    ),
    company_live_team: bool = typer.Option(
        False,
        "--live-team",
        help="Company-run only: allow native OMX Team launch instead of planned dispatch evidence.",
    ),
    company_team_launch: str = typer.Option(
        CompanyRunTeamLaunchMode.LAUNCH.value,
        "--team-launch",
        help="Company-run only: Team handling mode, launch or handoff.",
    ),
    company_worker_count: int = typer.Option(
        4,
        "--worker-count",
        help="Company-run only: Team worker count, minimum 3.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Codex model override for Codex-backed steps, company-run council lanes, and Team workers.",
    ),
    reasoning_effort: str | None = typer.Option(
        None,
        "--reasoning-effort",
        help="Codex reasoning effort override: low, medium, high, or xhigh.",
    ),
    xhigh: bool = typer.Option(
        False,
        "--xhigh",
        help="Shortcut for --reasoning-effort xhigh.",
    ),
    madmax: bool = typer.Option(
        False,
        "--madmax",
        help="DANGEROUS: request xhigh reasoning plus Codex approval/sandbox bypass.",
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
        timeout_sec [float | None]: Per-step subprocess timeout.
        max_attempts [int]: Maximum attempts for retryable steps.
        provider [str | None]: One-off prompt provider.
        prompt_file [Path | None]: Optional one-off prompt file.
        inline_prompt [str | None]: Optional one-off inline prompt.
        json_output [bool]: Whether to print JSON.
        record_run [bool]: Whether to write a run record.
        company_council_mode [str]: Company-run council mode.
        company_live_team [bool]: Whether company-run may launch native OMX Team.
        company_team_launch [str]: Company-run Team handling mode.
        company_worker_count [int]: Company-run Team worker count.
        model [str | None]: Optional Codex model override.
        reasoning_effort [str | None]: Optional Codex reasoning effort override.
        xhigh [bool]: Shortcut for xhigh reasoning.
        madmax [bool]: Dangerous approval/sandbox bypass shortcut.
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
        runtime_options: CommandRuntimeOptions | None = build_command_runtime_options(
            model=model,
            reasoning_effort=reasoning_effort,
            xhigh=xhigh,
            madmax=madmax,
        )

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
            task_text=task,
            runtime_options=runtime_options,
        )
        if dry_run and record_run:
            run_record = write_dry_run_record(plan, cwd=cwd)
        if execute:
            autonomy_mode = CommandAutonomyMode(autonomy)
            if recipe.display_id == "company-run":
                company_timeout_seconds = (
                    COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS
                    if timeout_sec is None
                    else timeout_sec
                )
                parsed_council_mode = CompanyRunCouncilMode(company_council_mode)
                parsed_team_launch = CompanyRunTeamLaunchMode(company_team_launch)
                company_request = CompanyRunExecutionRequest(
                    objective=task or recipe.description,
                    cwd=str(Path(cwd).resolve()),
                    autonomy=autonomy_mode.value,
                    council_mode=parsed_council_mode,
                    live_team_allowed=company_live_team,
                    team_launch_mode=parsed_team_launch,
                    worker_count=company_worker_count,
                    timeout_seconds=company_timeout_seconds,
                    runtime_options=runtime_options,
                )
                company_result = company_run_engine.execute_company_run(company_request)
                if json_output:
                    typer.echo(company_result.model_dump_json(indent=2))
                    company_exit_code = _company_run_exit_code(company_result.status)
                    if company_exit_code != 0:
                        raise typer.Exit(code=company_exit_code)
                    return
                typer.echo(_format_company_run_human(company_result))
                company_exit_code = _company_run_exit_code(company_result.status)
                if company_exit_code != 0:
                    raise typer.Exit(code=company_exit_code)
                return
            executor_timeout_seconds = 120.0 if timeout_sec is None else timeout_sec
            executor = CommandExecutor(
                max_attempts=max_attempts, timeout_seconds=executor_timeout_seconds
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
