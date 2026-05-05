import asyncio

import typer

from omx_remote.bridge.adapter_envelope import read_adapter_envelope
from omx_remote.bridge.adapter_probe import probe_adapter
from omx_remote.bridge.adapter_status import read_adapter_status
from omx_remote.execution.invoke import run_omx_command
from omx_remote.history.session_search import search_sessions
from omx_remote.runtime.active_runtime_modes import read_active_runtime_modes
from omx_remote.runtime.ralph_control import (
    build_ralph_launch_plan,
    build_ralph_resume_plan,
    cleanup_ralph_state,
    format_preflight_failure,
    format_resume_outcome,
)
from omx_remote.runtime.runtime_mode_state import read_runtime_mode_state
from omx_remote.runtime.runtime_mode_status import read_runtime_mode_status
from omx_remote.runtime.runtime_snapshot import read_runtime_status
from omx_remote.runtime.ultrawork_control import (
    build_ultrawork_launch_plan,
    build_ultrawork_resume_plan,
    cleanup_ultrawork_state,
    format_preflight_failure as format_ultrawork_preflight_failure,
    format_resume_outcome as format_ultrawork_resume_outcome,
)
from omx_remote.schemas.bridge_schemas import AdapterProbeRequest
from omx_remote.schemas.history_schemas import SessionSearchRequest
from omx_remote.schemas.runtime_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStatusRequest,
    RuntimeStatusRequest,
)
from omx_remote.schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
    TeamApiReadWorkerStatusRequest,
    TeamAwaitRequest,
    TeamStatusRequest,
)
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
    read_team_api_read_worker_status,
)
from omx_remote.teamwork.team_snapshot import await_team_status, read_team_status

HELP_TEXT = """Agent-facing adapter layer for operating OMX as a stateful runtime.

Supported commands expose currently implemented read-oriented OMX surfaces.
Use subcommand --help to see available operations for each domain.
"""

app = typer.Typer(help=HELP_TEXT, add_completion=False)
runtime_app = typer.Typer(help="Read OMX runtime and mode state.", add_completion=False)
team_app = typer.Typer(help="Read OMX team runtime and team API state.", add_completion=False)
history_app = typer.Typer(help="Read OMX session history search results.", add_completion=False)
adapt_app = typer.Typer(help="Read OMX adapter probe, status, and envelope surfaces.", add_completion=False)
ralph_app = typer.Typer(help="Read Ralph-related OMX runtime state.", add_completion=False)
ultrawork_app = typer.Typer(help="Read/operate Ultrawork-related OMX runtime state.", add_completion=False)

app.add_typer(runtime_app, name="runtime")
app.add_typer(team_app, name="team")
app.add_typer(history_app, name="history")
app.add_typer(adapt_app, name="adapt")
app.add_typer(ralph_app, name="ralph")
app.add_typer(ultrawork_app, name="ultrawork")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show the top-level help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Show the current package version."""
    typer.echo("agent-remote 0.1.0")


@runtime_app.command("status")
def runtime_status() -> None:
    """Read normalized OMX runtime status."""
    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("active-modes")
def runtime_active_modes() -> None:
    """Read active OMX runtime modes."""
    result = asyncio.run(read_active_runtime_modes())
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("mode-status")
def runtime_mode_status(mode: str = typer.Option(..., "--mode", help="OMX mode name to inspect.")) -> None:
    """Read normalized OMX state get-status result for one mode."""
    result = asyncio.run(read_runtime_mode_status(RuntimeModeStatusRequest(mode=mode)))
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("mode-state")
def runtime_mode_state(mode: str = typer.Option(..., "--mode", help="OMX mode name to inspect.")) -> None:
    """Read normalized OMX state read result for one mode."""
    result = asyncio.run(read_runtime_mode_state(RuntimeModeStateRequest(mode=mode)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("status")
def team_status(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
    """Read normalized OMX team status."""
    result = asyncio.run(read_team_status(TeamStatusRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("await-event")
def team_await_event(
    team: str = typer.Option(..., "--team", help="Team name to inspect."),
    timeout_ms: int = typer.Option(1000, "--timeout-ms", help="Wait timeout in milliseconds."),
) -> None:
    """Read one normalized OMX team await snapshot."""
    _ = timeout_ms
    result = asyncio.run(await_team_status(TeamAwaitRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("tasks")
def team_tasks(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
    """Read normalized OMX team task list."""
    result = asyncio.run(read_team_api_list_tasks(TeamApiListTasksRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("events")
def team_events(team: str = typer.Option(..., "--team", help="Team name to inspect.")) -> None:
    """Read normalized OMX team event list."""
    result = asyncio.run(read_team_api_read_events(TeamApiReadEventsRequest(team_name=team)))
    typer.echo(result.model_dump_json(indent=2))


@team_app.command("worker-status")
def team_worker_status(
    team: str = typer.Option(..., "--team", help="Team name to inspect."),
    worker: str = typer.Option(..., "--worker", help="Worker name to inspect."),
) -> None:
    """Read normalized OMX team worker status."""
    result = asyncio.run(
        read_team_api_read_worker_status(
            TeamApiReadWorkerStatusRequest(team_name=team, worker=worker)
        )
    )
    typer.echo(result.model_dump_json(indent=2))


@history_app.command("session-search")
def history_session_search(
    query: str = typer.Option(..., "--query", help="Search query to run against OMX session history."),
    limit: int = typer.Option(10, "--limit", help="Maximum number of results to return."),
) -> None:
    """Read normalized OMX session-search results."""
    result = asyncio.run(search_sessions(SessionSearchRequest(query=query, limit=limit)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("probe")
def adapt_probe(target: str = typer.Option(..., "--target", help="Adapter target name to inspect.")) -> None:
    """Read normalized OMX adapter probe output."""
    result = asyncio.run(probe_adapter(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("status")
def adapt_status(target: str = typer.Option(..., "--target", help="Adapter target name to inspect.")) -> None:
    """Read normalized OMX adapter status output."""
    result = asyncio.run(read_adapter_status(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("envelope")
def adapt_envelope(target: str = typer.Option(..., "--target", help="Adapter target name to inspect.")) -> None:
    """Read normalized OMX adapter envelope output."""
    result = asyncio.run(read_adapter_envelope(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@ralph_app.command("snapshot")
def ralph_snapshot() -> None:
    """Read the current normalized runtime snapshot and inspect Ralph-related state."""
    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))
    typer.echo(result.model_dump_json(indent=2))


@ralph_app.command("startability")
def ralph_startability() -> None:
    """Read Ralph mode state and mode status to assess whether Ralph can be inspected or resumed safely."""
    mode_state = asyncio.run(read_runtime_mode_state(RuntimeModeStateRequest(mode="ralph")))
    mode_status = asyncio.run(read_runtime_mode_status(RuntimeModeStatusRequest(mode="ralph")))
    typer.echo(
        {
            "mode_state": mode_state.model_dump(),
            "mode_status": mode_status.model_dump(),
        }
    )


@ralph_app.command("launch")
def ralph_launch(
    task: str = typer.Option(..., "--task", help="Task text to pass to omx ralph --prd."),
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
) -> None:
    """Launch Ralph through the OMX CLI PRD-gated startup path."""
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

    command_result = run_omx_command(command)
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

    command_result = run_omx_command(command)
    command_result = format_resume_outcome(command_result)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ralph_app.command("cleanup-stale")
def ralph_cleanup_stale() -> None:
    """Remove common stale Ralph state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ralph_state()
    typer.echo({"removed": removed_paths})


@ultrawork_app.command("launch")
def ultrawork_launch(
    task: str = typer.Option(..., "--task", help="Task text to pass to `omx team [N:role] \"<task>\"`."),
    team_size: int = typer.Option(
        1,
        "--team-size",
        help="Team size to allocate for the task (defaults to 1).",
    ),
    team_role: str = typer.Option(
        "executor",
        "--team-role",
        help="Team worker role to use for the launch prefix (defaults to executor).",
    ),
    force_cleanup: bool = typer.Option(
        False,
        "--force-cleanup",
        help="Allow launch to proceed even when known Ultrawork state files already exist.",
    ),
    allow_non_tty: bool = typer.Option(
        False,
        "--allow-non-tty",
        help="Allow launch from a non-interactive stdin environment when you know upstream behavior is acceptable.",
    ),
) -> None:
    """Launch Ultrawork through `omx team [N:role]` with state-aware guardrails."""
    try:
        command, preflight_warnings = build_ultrawork_launch_plan(
            task,
            force_cleanup=force_cleanup,
            allow_non_tty=allow_non_tty,
            team_size=team_size,
            team_role=team_role,
        )
    except ValueError as error:
        command_result = format_ultrawork_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = run_omx_command(command)
    typer.echo(command_result.model_dump_json(indent=2))


@ultrawork_app.command("resume")
def ultrawork_resume(
    team_name: str = typer.Option(..., "--team-name", help="Team name to resume."),
) -> None:
    """Resume Ultrawork through `omx team resume <team-name>`."""
    try:
        command, preflight_warnings = build_ultrawork_resume_plan(team_name)
    except ValueError as error:
        command_result = format_ultrawork_preflight_failure(str(error))
        typer.echo(command_result.model_dump_json(indent=2))
        raise typer.Exit(code=2) from error

    for warning in preflight_warnings:
        typer.echo(f"warning: {warning}")

    command_result = run_omx_command(command)
    command_result = format_ultrawork_resume_outcome(command_result, team_name=team_name)
    typer.echo(command_result.model_dump_json(indent=2))
    if command_result.exit_code != 0:
        raise typer.Exit(code=command_result.exit_code)


@ultrawork_app.command("cleanup-stale")
def ultrawork_cleanup_stale() -> None:
    """Remove common stale Ultrawork state files from the current OMX workspace."""
    removed_paths: list[str] = cleanup_ultrawork_state()
    typer.echo({"removed": removed_paths})


if __name__ == "__main__":
    app()
