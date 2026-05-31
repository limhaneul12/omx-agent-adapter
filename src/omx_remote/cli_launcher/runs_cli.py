from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.runtime.runs.run_record_reader import (
    build_run_replay_plan,
    list_run_records,
    read_run_handoff,
    read_run_record,
)
from omx_remote.schemas.runs.run_record_schemas import (
    RunListResult,
    RunRecord,
    RunReplayPlan,
)

runs_app = typer.Typer(
    help="Inspect recorded composed-command runs under .agent-remote/runs.",
    add_completion=False,
)


def _format_run_list_human(result: RunListResult) -> str:
    """Format run list output for humans.

    Args:
        result [RunListResult]: Run list result.

    Returns:
        str: Human-readable run list.
    """
    if not result.records:
        empty_text: str = "No run records found."
        return empty_text

    lines: list[str] = [
        f"{record.run_id}\t{record.status}\t{record.qualified_id}"
        for record in result.records
    ]
    rendered_text: str = "\n".join(lines)
    return rendered_text


def _raise_runs_error(error: Exception, json_output: bool) -> None:
    """Render a runs CLI error and exit without a traceback.

    Args:
        error [Exception]: Error to render.
        json_output [bool]: Whether to print JSON.
    """
    if json_output:
        typer.echo(_format_error_payload(error))
    else:
        typer.echo(str(error))
    raise typer.Exit(code=2) from error


@runs_app.command("list")
def runs_list(
    cwd: Path = typer.Option(Path("."), "--cwd", help="Repository root to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """List recorded runs.

    Args:
        cwd [Path]: Repository root to inspect.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        result: RunListResult = list_run_records(cwd)
    except (OSError, ValueError, ValidationError, orjson.JSONDecodeError) as error:
        _raise_runs_error(error, json_output)
        return

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_run_list_human(result))


@runs_app.command("show")
def runs_show(
    run_id: str = typer.Argument(..., help="Run id to show."),
    cwd: Path = typer.Option(Path("."), "--cwd", help="Repository root to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Show one run record.

    Args:
        run_id [str]: Run id to show.
        cwd [Path]: Repository root to inspect.
        json_output [bool]: Whether to print JSON output.
    """
    try:
        record: RunRecord = read_run_record(cwd, run_id)
    except (OSError, ValueError, ValidationError, orjson.JSONDecodeError) as error:
        _raise_runs_error(error, json_output)
        return

    if json_output:
        typer.echo(record.model_dump_json(indent=2))
        return

    typer.echo(f"{record.run_id}: {record.status} {record.qualified_id}")


@runs_app.command("handoff")
def runs_handoff(
    run_id: str = typer.Argument(..., help="Run id to render."),
    cwd: Path = typer.Option(Path("."), "--cwd", help="Repository root to inspect."),
) -> None:
    """Render one run handoff artifact.

    Args:
        run_id [str]: Run id to render.
        cwd [Path]: Repository root to inspect.
    """
    try:
        handoff_text: str = read_run_handoff(cwd, run_id)
    except (OSError, ValueError, ValidationError, orjson.JSONDecodeError) as error:
        _raise_runs_error(error, json_output=False)
        return

    typer.echo(handoff_text)


@runs_app.command("replay-plan")
def runs_replay_plan(
    run_id: str = typer.Argument(..., help="Run id to replay."),
    cwd: Path = typer.Option(Path("."), "--cwd", help="Repository root to inspect."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Required replay safety flag."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Build a dry-run replay plan from a recorded run.

    Args:
        run_id [str]: Run id to replay.
        cwd [Path]: Repository root to inspect.
        dry_run [bool]: Required replay safety flag.
        json_output [bool]: Whether to print JSON output.
    """
    if not dry_run:
        raise typer.BadParameter("replay-plan requires --dry-run")

    try:
        replay: RunReplayPlan = build_run_replay_plan(cwd, run_id)
    except (OSError, ValueError, ValidationError, orjson.JSONDecodeError) as error:
        _raise_runs_error(error, json_output)
        return

    if json_output:
        typer.echo(replay.model_dump_json(indent=2))
        return

    typer.echo(f"replay: {replay.run_id}")
    typer.echo(f"command: {replay.plan.qualified_id}")
