import asyncio
from pathlib import Path

import typer

from omx_remote.runtime.cockpit.sources.agent_config import (
    summarize_cockpit_agent_config,
)
from omx_remote.runtime.cockpit.sources.capability_snapshot import (
    read_cockpit_capabilities,
)
from omx_remote.runtime.cockpit.sources.command_recipes import (
    summarize_cockpit_command_recipes,
)
from omx_remote.runtime.routes.route_explanation_renderer import (
    explain_route,
    render_route_policy_human,
)
from omx_remote.runtime.routes.route_policy_engine import build_route_policy_result
from omx_remote.runtime.status.active_runtime_modes import read_active_runtime_modes
from omx_remote.schemas.route_policy_schemas import (
    RouteExplanation,
    RoutePolicyResult,
)
from omx_remote.schemas.runtime_status_schemas import ActiveRuntimeModes

route_app = typer.Typer(
    help="Classify tasks and recommend Codex/OMX/project execution routes.",
    add_completion=False,
)


def _read_task_text(task: str | None, task_file: Path | None) -> str:
    """Read task text from an inline task or task file.

    Args:
        task [str | None]: Inline task text.
        task_file [Path | None]: Optional file containing task text.

    Returns:
        str: Task text used for classification.
    """
    if task is not None:
        task_text: str = task
        return task_text
    if task_file is not None:
        task_text = task_file.read_text(encoding="utf-8")
        return task_text

    raise typer.BadParameter("Provide --task or --task-file.")


def _route_lines(result: RoutePolicyResult) -> tuple[str, ...]:
    """Build human-readable route recommendation lines.

    Args:
        result [RoutePolicyResult]: Route policy result.

    Returns:
        tuple[str, ...]: Human-readable route lines.
    """
    lines: list[str] = []
    for recommendation in result.recommendations:
        command_suffix: str = ""
        if recommendation.command_id is not None:
            command_suffix = f" ({recommendation.command_id})"
        lines.append(
            f"- {recommendation.route}{command_suffix}: {recommendation.reason}"
        )
    for alternative in result.blocked_alternatives:
        blocker_text: str = "; ".join(alternative.blocked_by)
        lines.append(f"- blocked {alternative.route}: {blocker_text}")

    route_lines: tuple[str, ...] = tuple(lines)
    return route_lines


@route_app.command("recommend")
def route_recommend(
    task: str | None = typer.Option(None, "--task", help="Task text to classify."),
    task_file: Path | None = typer.Option(
        None,
        "--task-file",
        help="Path to a markdown/text task file.",
    ),
    cwd: str = typer.Option(".", "--cwd", help="Repository root to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Recommend a route for a task.

    Args:
        task [str | None]: Inline task text.
        task_file [Path | None]: Optional task file.
        cwd [str]: Repository root to inspect.
        json_output [bool]: Whether to print JSON output.
    """
    repo_root: Path = Path(cwd).resolve()
    task_text: str = _read_task_text(task, task_file)
    active_runtime_modes: ActiveRuntimeModes = asyncio.run(read_active_runtime_modes())
    result: RoutePolicyResult = build_route_policy_result(
        task=task_text,
        cwd=repo_root,
        capabilities=read_cockpit_capabilities(),
        agent_summary=summarize_cockpit_agent_config(repo_root),
        recipe_summary=summarize_cockpit_command_recipes(repo_root),
        safe_to_mutate=not active_runtime_modes.active_modes,
        active_runtime_modes=active_runtime_modes.active_modes,
    )
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    summary: str = (
        f"classification: {result.classification.task_type}/"
        f"{result.classification.size}"
    )
    typer.echo(render_route_policy_human(summary, _route_lines(result)))


@route_app.command("explain")
def route_explain(
    route: str = typer.Argument(..., help="Route name using hyphens or underscores."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Explain one route.

    Args:
        route [str]: Route name using hyphens or underscores.
        json_output [bool]: Whether to print JSON output.
    """
    explanation: RouteExplanation = explain_route(route)
    if json_output:
        typer.echo(explanation.model_dump_json(indent=2))
        return

    typer.echo(f"{explanation.route}: {explanation.summary}")
    typer.echo(f"typical_use: {explanation.typical_use}")
    if explanation.preflight_route is not None:
        typer.echo(f"preflight_route: {explanation.preflight_route}")
