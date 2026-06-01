from pathlib import Path

from omx_remote.runtime.commands.catalog.command_catalog_resolver import (
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.planning.command_step_planner import (
    build_command_execution_plan,
)
from omx_remote.runtime.preflight.git_preflight import check_git_state
from omx_remote.runtime.preflight.prompt_file_preflight import check_prompt_file
from omx_remote.runtime.preflight.tool_preflight import check_tool_available
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandExecutionPlan,
    CommandPlanStep,
    CommandRecipe,
    CommandRisk,
)
from omx_remote.schemas.preflight_schemas import (
    PreflightCategory,
    PreflightCheckResult,
    PreflightReport,
    PreflightReportStatus,
    PreflightSeverity,
)


def _report_status(checks: tuple[PreflightCheckResult, ...]) -> PreflightReportStatus:
    """Derive aggregate status from checks.

    Args:
        checks [tuple[PreflightCheckResult, ...]]: Checks to summarize.

    Returns:
        PreflightReportStatus: Aggregate report status.
    """
    if any(check.severity == PreflightSeverity.BLOCKER for check in checks):
        status: PreflightReportStatus = PreflightReportStatus.BLOCKED
        return status
    if any(check.severity == PreflightSeverity.WARNING for check in checks):
        status = PreflightReportStatus.WARNING
        return status

    status = PreflightReportStatus.PASSED
    return status


def _build_report(
    checks: tuple[PreflightCheckResult, ...],
    command_id: str | None = None,
    qualified_id: str | None = None,
    route: str | None = None,
) -> PreflightReport:
    """Build one aggregate preflight report.

    Args:
        checks [tuple[PreflightCheckResult, ...]]: Checks to summarize.
        command_id [str | None]: Optional command id.
        qualified_id [str | None]: Optional source-qualified command id.
        route [str | None]: Optional route id.

    Returns:
        PreflightReport: Aggregate preflight report.
    """
    blockers: tuple[str, ...] = tuple(
        check.summary for check in checks if check.severity == PreflightSeverity.BLOCKER
    )
    warnings: tuple[str, ...] = tuple(
        check.summary for check in checks if check.severity == PreflightSeverity.WARNING
    )
    report = PreflightReport(
        status=_report_status(checks),
        checks=checks,
        blockers=blockers,
        warnings=warnings,
        command_id=command_id,
        qualified_id=qualified_id,
        route=route,
    )
    return report


def _plan_blocker_checks(
    plan: CommandExecutionPlan,
) -> tuple[PreflightCheckResult, ...]:
    """Convert plan blockers into preflight checks.

    Args:
        plan [CommandExecutionPlan]: Dry-run command plan.

    Returns:
        tuple[PreflightCheckResult, ...]: Plan blocker checks.
    """
    checks: list[PreflightCheckResult] = [
        (
            PreflightCheckResult(
                category=PreflightCategory.CONFIG_VALIDITY,
                severity=PreflightSeverity.BLOCKER,
                summary=blocker,
                detail=blocker,
                blocks_execution=True,
            )
        )
        for blocker in plan.blocked_reasons
    ]
    plan_checks: tuple[PreflightCheckResult, ...] = tuple(checks)
    return plan_checks


def _tool_checks(
    plan_steps: tuple[CommandPlanStep, ...],
) -> tuple[PreflightCheckResult, ...]:
    """Build tool availability checks from planned argv.

    Args:
        plan_steps [tuple[CommandPlanStep, ...]]: Plan steps to inspect.

    Returns:
        tuple[PreflightCheckResult, ...]: Tool availability checks.
    """
    tool_names: list[str] = [
        step.native_argv[0] for step in plan_steps if step.native_argv
    ]

    seen_tools: set[str] = set()
    checks: list[PreflightCheckResult] = []
    for tool_name in tool_names:
        if tool_name in seen_tools:
            continue
        seen_tools.add(tool_name)
        checks.append(check_tool_available(tool_name))

    tool_checks: tuple[PreflightCheckResult, ...] = tuple(checks)
    return tool_checks


def _prompt_checks(
    plan_steps: tuple[CommandPlanStep, ...], cwd: str | Path
) -> tuple[PreflightCheckResult, ...]:
    """Build prompt-file checks from planned steps.

    Args:
        plan_steps [tuple[CommandPlanStep, ...]]: Plan steps to inspect.
        cwd [str | Path]: Working directory.

    Returns:
        tuple[PreflightCheckResult, ...]: Prompt-file checks.
    """
    checks: list[PreflightCheckResult] = [
        check_prompt_file(cwd, step.prompt_file)
        for step in plan_steps
        if step.prompt_file is not None
    ]
    prompt_checks: tuple[PreflightCheckResult, ...] = tuple(checks)
    return prompt_checks


def run_command_preflight(
    command_id: str,
    cwd: str | Path,
    config_path: str | Path | None = None,
) -> PreflightReport:
    """Run reusable preflight checks for a command recipe.

    Args:
        command_id [str]: Qualified or unambiguous command id.
        cwd [str | Path]: Working directory.
        config_path [str | Path | None]: Optional config override.

    Returns:
        PreflightReport: Aggregate command preflight report.
    """
    catalog = load_command_catalog(cwd=cwd, config_path=config_path)
    recipe: CommandRecipe = resolve_command_recipe(catalog, command_id)
    plan: CommandExecutionPlan = build_command_execution_plan(
        recipe, cwd=cwd, dry_run=True
    )
    checks: tuple[PreflightCheckResult, ...] = (
        check_git_state(cwd, recipe.risk),
        *_tool_checks(plan.steps),
        *_prompt_checks(plan.steps, cwd),
        *_plan_blocker_checks(plan),
    )
    report: PreflightReport = _build_report(
        checks,
        command_id=recipe.id,
        qualified_id=recipe.qualified_id,
    )
    return report


def run_route_preflight(route: str, cwd: str | Path) -> PreflightReport:
    """Run reusable preflight checks for a named route.

    Args:
        route [str]: Route id, for example `omx-team`.
        cwd [str | Path]: Working directory.

    Returns:
        PreflightReport: Aggregate route preflight report.
    """
    if route == "omx-team":
        checks: tuple[PreflightCheckResult, ...] = (
            check_git_state(cwd, CommandRisk.LAUNCHES_RUNTIME),
            check_tool_available("omx"),
        )
    elif route == "omx-ultragoal":
        checks = (
            check_git_state(cwd, CommandRisk.LAUNCHES_RUNTIME),
            check_tool_available("omx"),
        )
    elif route == "codex-exec":
        checks = (
            check_git_state(cwd, CommandRisk.READ_ONLY),
            check_tool_available("codex"),
        )
    else:
        checks = (
            PreflightCheckResult(
                category=PreflightCategory.CAPABILITY_SUPPORT,
                severity=PreflightSeverity.WARNING,
                summary=f"route {route} has no specialized preflight profile",
                detail="Only generic route diagnostics are available.",
                blocks_execution=False,
            ),
        )

    report = _build_report(checks, route=route)
    return report
