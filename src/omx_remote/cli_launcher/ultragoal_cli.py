import typer

from omx_remote.runtime.ultragoal.ultragoal_status import read_ultragoal_status
from omx_remote.schemas.ultragoal_status_schemas import UltragoalStatusResult

ultragoal_app = typer.Typer(
    help="Read native OMX UltraGoal capability and status.",
    add_completion=False,
)


def _format_ultragoal_status_summary(result: UltragoalStatusResult) -> str:
    """Format UltraGoal status for humans.

    Args:
        result [UltragoalStatusResult]: Typed native UltraGoal status result.

    Returns:
        str: Human-readable status summary.
    """
    lines: list[str] = [
        f"state: {result.state}",
        f"supported: {result.supported}",
        f"capability_exit_code: {result.capability_result.exit_code}",
    ]
    if result.status_result is not None:
        lines.append(f"status_exit_code: {result.status_result.exit_code}")
    lines.extend(f"warning: {warning}" for warning in result.warnings)
    status_summary: str = "\n".join(lines)
    return status_summary


@ultragoal_app.command("status")
def ultragoal_status(
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional working directory where native OMX UltraGoal status should be read.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed UltraGoal status result as JSON.",
    ),
) -> None:
    """Read native OMX UltraGoal status through a typed adapter surface.

    Args:
        cwd [str | None]: Optional working directory where native OMX probes run.
        json_output [bool]: Whether to print JSON instead of a human summary.
    """
    result: UltragoalStatusResult = read_ultragoal_status(cwd=cwd)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_ultragoal_status_summary(result))
