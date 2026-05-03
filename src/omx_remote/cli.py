import typer

HELP_TEXT = """Agent-facing adapter layer for operating OMX as a stateful runtime.

Quick start:
  - uv run agent-remote --help
  - uv run agent-remote version

Current scope:
  - typed runtime status reads
  - typed teamwork status and event reads
  - typed adapter probe/status/envelope reads
  - execution/event normalization utilities for OMX JSON surfaces
"""

app = typer.Typer(help=HELP_TEXT, add_completion=False)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show the top-level help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def version() -> None:
    """Show the current package version."""
    typer.echo("agent-remote 0.1.0")


if __name__ == "__main__":
    app()
