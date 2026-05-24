import typer

from omx_remote.cli_launcher.adapt_cli import adapt_app
from omx_remote.cli_launcher.agents_cli import agents_app
from omx_remote.cli_launcher.cockpit_cli import cockpit_app
from omx_remote.cli_launcher.goal_cli import goal_app
from omx_remote.cli_launcher.history_cli import history_app
from omx_remote.cli_launcher.prd_cli import prd_app
from omx_remote.cli_launcher.ralph_cli import ralph_app
from omx_remote.cli_launcher.runtime_cli import runtime_app
from omx_remote.cli_launcher.team_cli import team_app
from omx_remote.cli_launcher.ultragoal_cli import ultragoal_app
from omx_remote.cli_launcher.ultrawork_cli import ultrawork_app

HELP_TEXT = """Agent-facing control layer for using OMX + Codex strongly.

AI-friendly route guidance, typed state, evidence, and guardrails for Codex/OMX development lanes.
Use subcommand --help to see available operations for each domain.
"""

app = typer.Typer(help=HELP_TEXT, add_completion=False)
app.add_typer(runtime_app, name="runtime")
app.add_typer(cockpit_app, name="cockpit")
app.add_typer(team_app, name="team")
app.add_typer(history_app, name="history")
app.add_typer(adapt_app, name="adapt")
app.add_typer(agents_app, name="agents")
app.add_typer(goal_app, name="goal")
app.add_typer(prd_app, name="prd")
app.add_typer(ultragoal_app, name="ultragoal")
app.add_typer(ralph_app, name="ralph")
app.add_typer(ultrawork_app, name="ultrawork")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show the top-level help when no subcommand is provided.

    Args:
        ctx [typer.Context]: Function argument.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Show the current package version."""
    typer.echo("agent-remote 0.1.0")
