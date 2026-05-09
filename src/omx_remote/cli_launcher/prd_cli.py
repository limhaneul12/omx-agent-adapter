from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.prd.prd_capture import validate_and_capture_prd_artifact

PRD_HELP_TEXT = """Validate and capture Goal-scoped PRD artifacts before Ralph consumes them."""

prd_app = typer.Typer(help=PRD_HELP_TEXT, add_completion=False)


@prd_app.command("validate")
def prd_validate(
    input_path: Path = typer.Option(
        ...,
        "--input-path",
        help="Path to a generated PRD JSON artifact to validate as RalphPrdArtifact.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="Optional capture destination, usually .omx/prd.json for Ralph.",
    ),
) -> None:
    """Validate a generated PRD artifact and optionally capture it for Ralph.

    Args:
        input_path [Path]: Path to generated PRD JSON.
        output_path [Path | None]: Optional capture destination.
    """
    try:
        result = validate_and_capture_prd_artifact(
            input_path=input_path,
            output_path=output_path,
        )
    except (OSError, orjson.JSONDecodeError, ValidationError, ValueError) as error:
        typer.echo(str(error))
        raise typer.Exit(code=2) from error

    typer.echo(result.model_dump_json(indent=2))
