from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.runtime.preflight.command_preflight_runner import (
    run_command_preflight,
    run_route_preflight,
)
from omx_remote.runtime.preflight.prompt_file_preflight import check_prompt_file
from omx_remote.schemas.preflight.preflight_schemas import (
    PreflightCheckResult,
    PreflightReport,
)

preflight_app = typer.Typer(
    help="Run reusable preflight safety checks before command or route execution.",
    add_completion=False,
)


def _echo_report(report: PreflightReport, json_output: bool) -> None:
    """Print a preflight report.

    Args:
        report [PreflightReport]: Report to print.
        json_output [bool]: Whether to print JSON.
    """
    if json_output:
        typer.echo(report.model_dump_json(indent=2))
        return

    typer.echo(f"status: {report.status}")
    for check in report.checks:
        typer.echo(f"{check.severity}\t{check.category}\t{check.summary}")


@preflight_app.command("prompt-file")
def preflight_prompt_file(
    prompt_path: Path = typer.Argument(..., help="Prompt file to inspect."),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root the prompt file must be visible from.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed preflight report as JSON.",
    ),
) -> None:
    """Run prompt-file visibility preflight.

    Args:
        prompt_path [Path]: Prompt file to inspect.
        cwd [Path]: Working directory.
        json_output [bool]: Whether to print JSON.
    """
    try:
        check: PreflightCheckResult = check_prompt_file(cwd, prompt_path)
        status = "blocked" if check.blocks_execution else "passed"
        report = PreflightReport(status=status, checks=(check,), blockers=())
    except (ValidationError, ValueError, OSError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    _echo_report(report, json_output)


@preflight_app.command("run")
def preflight_run(
    command_id: str = typer.Argument(..., help="Qualified or unambiguous command id."),
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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed preflight report as JSON.",
    ),
) -> None:
    """Run command-recipe preflight checks.

    Args:
        command_id [str]: Qualified or unambiguous command id.
        cwd [Path]: Working directory.
        config_path [Path | None]: Optional command config override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        report: PreflightReport = run_command_preflight(
            command_id,
            cwd=cwd,
            config_path=config_path,
        )
    except (ValidationError, ValueError, OSError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    _echo_report(report, json_output)


@preflight_app.command("route")
def preflight_route(
    route: str = typer.Argument(..., help="Route id such as omx-team or codex-exec."),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used for route preflight.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed preflight report as JSON.",
    ),
) -> None:
    """Run route-level preflight checks.

    Args:
        route [str]: Route id.
        cwd [Path]: Working directory.
        json_output [bool]: Whether to print JSON.
    """
    try:
        report: PreflightReport = run_route_preflight(route, cwd=cwd)
    except (ValidationError, ValueError, OSError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    _echo_report(report, json_output)
