import typer

from omx_remote.schemas.invoke.command_schemas import OmxCommandResult


def echo_omx_command_result(result: OmxCommandResult) -> None:
    """Print one OMX command result and propagate its shell exit code.

    Args:
        result [OmxCommandResult]: Command result to print and inspect.
    """
    typer.echo(result.model_dump_json(indent=2))
    if result.exit_code != 0:
        raise typer.Exit(code=result.exit_code)
