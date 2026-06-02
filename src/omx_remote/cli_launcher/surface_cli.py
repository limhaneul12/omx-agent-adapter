from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.cli_launcher.cli_error_payload import (
    format_failed_cli_error_payload as _format_error_payload,
)
from omx_remote.runtime.control_surface_inventory import (
    build_comx_control_surface_inventory,
)
from omx_remote.schemas.control_surface_schemas import ComxControlSurfaceInventory


def _format_surface_human(inventory: ComxControlSurfaceInventory) -> str:
    """Render comx-agent surface inventory as human-readable text.

    Args:
        inventory [ComxControlSurfaceInventory]: Typed inventory.

    Returns:
        str: Human-readable surface summary.
    """
    lines: list[str] = [
        f"product: {inventory.product_name}",
        "native_commands:",
    ]
    lines.extend(
        f"- {command.name}: {command.description}"
        for command in inventory.native_commands
    )
    lines.append("composed_commands:")
    lines.extend(
        f"- {command.qualified_id}: {command.description}"
        for command in inventory.composed_commands
    )
    rendered: str = "\n".join(lines)
    return rendered


def surface_command(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve command recipes.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command config path override.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    """Show what comx-agent supports natively versus via composed recipes.

    Args:
        cwd [Path]: Repository root.
        config_path [Path | None]: Optional config override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        inventory: ComxControlSurfaceInventory = build_comx_control_surface_inventory(
            cwd=cwd,
            config_path=config_path,
        )
    except (ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(inventory.model_dump_json(indent=2))
        return

    typer.echo(_format_surface_human(inventory))
