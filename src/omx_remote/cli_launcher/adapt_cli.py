import asyncio

import typer

from omx_remote.bridge.adapter_envelope import read_adapter_envelope
from omx_remote.bridge.adapter_probe import probe_adapter
from omx_remote.bridge.adapter_status import read_adapter_status
from omx_remote.schemas.bridge_adapter_schemas import AdapterProbeRequest

adapt_app = typer.Typer(
    help="Read OMX adapter probe, status, and envelope surfaces.", add_completion=False
)


@adapt_app.command("probe")
def adapt_probe(
    target: str = typer.Option(..., "--target", help="Adapter target name to inspect."),
) -> None:
    """Read normalized OMX adapter probe output.

    Args:
        target [str]: Function argument.
    """
    result = asyncio.run(probe_adapter(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("status")
def adapt_status(
    target: str = typer.Option(..., "--target", help="Adapter target name to inspect."),
) -> None:
    """Read normalized OMX adapter status output.

    Args:
        target [str]: Function argument.
    """
    result = asyncio.run(read_adapter_status(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))


@adapt_app.command("envelope")
def adapt_envelope(
    target: str = typer.Option(..., "--target", help="Adapter target name to inspect."),
) -> None:
    """Read normalized OMX adapter envelope output.

    Args:
        target [str]: Function argument.
    """
    result = asyncio.run(read_adapter_envelope(AdapterProbeRequest(target=target)))
    typer.echo(result.model_dump_json(indent=2))
