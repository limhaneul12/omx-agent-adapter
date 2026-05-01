import typer

app = typer.Typer(help="Agent-facing adapter layer for operating OMX as a stateful runtime.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("omx-agent-adapter")


@app.command()
def version() -> None:
    """Show the current package version placeholder."""
    typer.echo("omx-agent-adapter 0.1.0")


if __name__ == "__main__":
    app()
