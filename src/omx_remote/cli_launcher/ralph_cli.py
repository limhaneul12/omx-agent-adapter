import asyncio
from collections.abc import Sequence
from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.cli_launcher import cli_facade_dependencies
from omx_remote.runtime.ralph.ralph_control import (
    build_ralph_launch_plan,
    build_ralph_resume_plan,
    build_ralph_team_launch_plan,
    format_preflight_failure,
    format_resume_outcome,
)
from omx_remote.runtime.ralph.ralph_post_team_review import build_ralph_post_team_review
from omx_remote.runtime.ralph.ralph_review_artifacts import (
    read_ralph_prd_artifact_file,
    read_team_admin_aggregation_report_artifact,
    write_ralph_post_team_review_artifact,
)
from omx_remote.runtime.ralph.ralph_state import cleanup_ralph_state
from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewRequest
from omx_remote.schemas.runtime_status_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStatusRequest,
    RuntimeStatusRequest,
)
from omx_remote.shared.utils.json_model_dump import model_json_object

ralph_app = typer.Typer(
    help="Read Ralph-related OMX runtime state.", add_completion=False
)


def _run_omx_command(command: Sequence[str]):
    """Run one OMX command through the public CLI facade dependency.

    Args:
        command [Sequence[str]]: Function argument.

    Returns:
        object: CLI facade command result.
    """
    command_result = cli_facade_dependencies.run_omx_command(command)
    return command_result


def _run_omx_command_inherited_stdio(command: Sequence[str]):
    """Run one OMX command while inheriting terminal stdio.

    Args:
        command [Sequence[str]]: OMX command arguments without executable name.

    Returns:
        object: CLI facade command result.
    """
    command_result = cli_facade_dependencies.run_omx_command_inherited_stdio(command)
    return command_result


def _read_runtime_mode_state(request: RuntimeModeStateRequest):
    """Read Ralph mode state through the public CLI facade dependency.

    Args:
        request [RuntimeModeStateRequest]: Function argument.

    Returns:
        object: Runtime mode state result.
    """
    return cli_facade_dependencies.read_runtime_mode_state(request)


def _read_runtime_mode_status(request: RuntimeModeStatusRequest):
    """Read Ralph mode status through the public CLI facade dependency.

    Args:
        request [RuntimeModeStatusRequest]: Function argument.

    Returns:
        object: Runtime mode status result.
    """
    return cli_facade_dependencies.read_runtime_mode_status(request)


@ralph_app.command("snapshot")
def ralph_snapshot() -> None:
    """Read the current normalized runtime snapshot and inspect Ralph-related state."""
    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))
    typer.echo(result.model_dump_json(indent=2))


@ralph_app.command("startability")
def ralph_startability() -> None:
    """Read Ralph mode state and mode status to assess whether Ralph can be inspected or resumed safely."""
    mode_state = asyncio.run(
        _read_runtime_mode_state(RuntimeModeStateRequest(mode="ralph"))
    )
    mode_status = asyncio.run(
        _read_runtime_mode_status(RuntimeModeStatusRequest(mode="ralph"))
    )
    output_payload = {
        "mode_state": model_json_object(mode_state),
        "mode_status": model_json_object(mode_status),
    }
    typer.echo(orjson.dumps(output_payload, option=orjson.OPT_INDENT_2).decode())


@ralph_app.command("review-team")
def ralph_review_team(
    prd_path: Path = typer.Option(
        ...,
        "--prd-path",
        help="Path to the RalphPrdArtifact JSON file.",
    ),
    admin_report: Path = typer.Option(
        ...,
        "--admin-report",
        help="Path to the TeamAdminAggregationReport JSON file.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="Optional path where the Ralph post-Team review JSON should be written.",
    ),
) -> None:
    """Review Team Admin aggregation against a Ralph PRD artifact.

    Args:
        prd_path [Path]: Path to the Ralph PRD artifact JSON file.
        admin_report [Path]: Path to the Team Admin aggregation report JSON file.
        output_path [Path | None]: Optional JSON artifact destination.
    """
    try:
        prd_artifact = read_ralph_prd_artifact_file(prd_path)
        aggregation_report = read_team_admin_aggregation_report_artifact(admin_report)
        request = RalphPostTeamReviewRequest(
            ralph_prd_artifact=prd_artifact,
            aggregation_report=aggregation_report,
        )
        review_result = build_ralph_post_team_review(request)
        if output_path is not None:
            write_ralph_post_team_review_artifact(review_result, output_path)
    except (OSError, orjson.JSONDecodeError, ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(review_result.model_dump_json(indent=2))


@ralph_app.command("launch")
def ralph_launch(
    task: str = typer.Option(
        ..., "--task", help="Task text to pass to omx ralph --prd."
    ),
    force_cleanup: bool = typer.Option(
        False,
        "--force-cleanup",
        help="Allow launch to proceed even when known Ralph state files already exist.",
    ),
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow launch from a non-interactive stdin environment when you know upstream behavior is acceptable.",
    ),
    inherit_stdio: bool = typer.Option(
        False,
        "--inherit-stdio",
        help="Run OMX with inherited terminal stdin/stdout/stderr for interactive Ralph startup.",
    ),
) -> None:
    """Launch Ralph through the OMX CLI PRD-gated startup path.

    Args:
        task [str]: Function argument.
        force_cleanup [bool]: Function argument.
        allow_non_tty [bool]: Function argument.
        inherit_stdio [bool]: Function argument.
    """
    try:
        command, preflight_warnings = build_ralph_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
        )
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    if inherit_stdio:
        command_result = _run_omx_command_inherited_stdio(command)
    else:
        command_result = _run_omx_command(command)
    typer.echo(command_result.model_dump_json(indent=2))


@ralph_app.command("launch-team")
def ralph_launch_team(
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow Team launch planning from a non-interactive stdin environment when upstream behavior is acceptable.",
    ),
    inherit_stdio: bool = typer.Option(
        False,
        "--inherit-stdio",
        help="Run OMX with inherited terminal stdin/stdout/stderr for interactive Team startup.",
    ),
    plan_only: bool = typer.Option(
        False,
        "--plan-only",
        help="Only write the Ralph-owned Team DAG handoff artifacts and print the OMX command; do not launch OMX.",
    ),
) -> None:
    """Launch or plan the Ralph-owned Team fanout from the typed Ralph PRD artifact.

    Args:
        allow_non_tty [bool]: Whether non-interactive Team launch planning is allowed.
        inherit_stdio [bool]: Whether to run OMX with inherited terminal stdio.
        plan_only [bool]: Whether to stop after writing the approved Team DAG handoff.
    """
    try:
        command, preflight_warnings = build_ralph_team_launch_plan(
            allow_non_tty=allow_non_tty,
            require_live_owner_preflight=not plan_only,
        )
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    if plan_only:
        plan_payload = {
            "command": command,
            "warnings": preflight_warnings,
            "planned_only": True,
        }
        typer.echo(orjson.dumps(plan_payload, option=orjson.OPT_INDENT_2).decode())
        return

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    if inherit_stdio:
        command_result = _run_omx_command_inherited_stdio(command)
    else:
        command_result = _run_omx_command(command)
    typer.echo(command_result.model_dump_json(indent=2))


@ralph_app.command("resume")
def ralph_resume() -> None:
    """Resume Ralph through the OMX CLI runtime surface."""
    try:
        command, preflight_warnings = build_ralph_resume_plan()
    except ValueError as error:
        command_result = format_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = _run_omx_command(command)
    command_result = format_resume_outcome(command_result)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ralph_app.command("cleanup-stale")
def ralph_cleanup_stale() -> None:
    """Remove common stale Ralph state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ralph_state()
    typer.echo({"removed": removed_paths})
