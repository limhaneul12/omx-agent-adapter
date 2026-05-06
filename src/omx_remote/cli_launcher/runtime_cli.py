import asyncio

import typer

from omx_remote.runtime.status.active_runtime_modes import read_active_runtime_modes
from omx_remote.runtime.status.runtime_mode_state import read_runtime_mode_state
from omx_remote.runtime.status.runtime_mode_status import read_runtime_mode_status
from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStatusRequest,
    RuntimeStatusRequest,
)

runtime_app = typer.Typer(help="Read OMX runtime and mode state.", add_completion=False)


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
    """Read normalized OMX state get-status result for one mode.
    
    Args:
        mode [str]: Function argument.
    """
    result = asyncio.run(read_runtime_mode_status(RuntimeModeStatusRequest(mode=mode)))
    typer.echo(result.model_dump_json(indent=2))


@runtime_app.command("mode-state")
def runtime_mode_state(mode: str = typer.Option(..., "--mode", help="OMX mode name to inspect.")) -> None:
    """Read normalized OMX state read result for one mode.
    
    Args:
        mode [str]: Function argument.
    """
    result = asyncio.run(read_runtime_mode_state(RuntimeModeStateRequest(mode=mode)))
    typer.echo(result.model_dump_json(indent=2))
