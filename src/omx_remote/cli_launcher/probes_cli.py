from pathlib import Path

import typer

from omx_remote.runtime.probes.codex_probe_suite import run_codex_probe_suite
from omx_remote.runtime.probes.omx_probe_suite import run_omx_probe_suite
from omx_remote.runtime.probes.probe_command_runner import (
    ProbeRunner,
    run_probe_command,
)
from omx_remote.runtime.probes.probe_fixture_comparator import (
    compare_probe_fixture,
    list_probe_fixtures,
)
from omx_remote.schemas.probes.upstream_probe_schemas import (
    ProbeFixtureComparison,
    ProbeFixtureListResult,
    UpstreamProbeSuiteResult,
)

probes_app = typer.Typer(
    help="Run and compare upstream Codex/OMX command contract probes.",
    add_completion=False,
)


def _run_suite(suite_id: str, runner: ProbeRunner) -> UpstreamProbeSuiteResult:
    """Run one named probe suite.

    Args:
        suite_id [str]: Probe suite id.
        runner [ProbeRunner]: Probe runner dependency.

    Returns:
        UpstreamProbeSuiteResult: Probe suite result.
    """
    if suite_id == "codex-basic":
        result: UpstreamProbeSuiteResult = run_codex_probe_suite(runner)
        return result
    if suite_id == "omx-basic":
        result = run_omx_probe_suite(runner)
        return result

    raise typer.BadParameter(f"unknown probe suite: {suite_id}")


def _format_suite_human(result: UpstreamProbeSuiteResult) -> str:
    """Format a probe suite for humans.

    Args:
        result [UpstreamProbeSuiteResult]: Probe suite result.

    Returns:
        str: Human-readable probe summary.
    """
    lines: list[str] = [
        f"suite: {result.suite_id}",
        f"target: {result.target}",
        f"supported: {result.supported_count}",
        f"unsupported: {result.unsupported_count}",
    ]
    lines.extend(
        f"- {probe.capability}: {probe.support_status}" for probe in result.results
    )
    text: str = "\n".join(lines)
    return text


@probes_app.command("run")
def probes_run(
    suite_id: str = typer.Argument(..., help="Probe suite id, e.g. codex-basic."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Run one upstream contract probe suite.

    Args:
        suite_id [str]: Probe suite id.
        json_output [bool]: Whether to print JSON output.
    """
    result: UpstreamProbeSuiteResult = _run_suite(suite_id, run_probe_command)
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_suite_human(result))


@probes_app.command("list-fixtures")
def probes_list_fixtures(
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """List sanitized probe fixtures.

    Args:
        json_output [bool]: Whether to print JSON output.
    """
    result: ProbeFixtureListResult = list_probe_fixtures()
    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    if not result.fixtures:
        typer.echo("No probe fixtures found.")
        return
    typer.echo("\n".join(result.fixtures))


@probes_app.command("compare")
def probes_compare(
    fixture: Path = typer.Option(..., "--fixture", help="Fixture JSON path."),
    suite_id: str = typer.Option("omx-basic", "--suite", help="Probe suite id."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Compare live probe evidence with a fixture.

    Args:
        fixture [Path]: Fixture JSON path.
        suite_id [str]: Probe suite id.
        json_output [bool]: Whether to print JSON output.
    """
    current: UpstreamProbeSuiteResult = _run_suite(suite_id, run_probe_command)
    comparison: ProbeFixtureComparison = compare_probe_fixture(fixture, current)
    if json_output:
        typer.echo(comparison.model_dump_json(indent=2))
        return

    typer.echo(f"matches: {comparison.matches}")
    typer.echo(f"added: {', '.join(comparison.added_capabilities)}")
    typer.echo(f"removed: {', '.join(comparison.removed_capabilities)}")
