from pathlib import Path

import orjson
import typer
from pydantic import ValidationError

from omx_remote.runtime.commands.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.command_recipe_loader import CommandRecipeLoadError
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandCatalogEntry,
    CommandCatalogListResult,
    CommandRecipe,
    CommandShowResult,
    CommandSource,
)

commands_app = typer.Typer(
    help="Inspect project-owned command catalog and repo-defined recipes.",
    add_completion=False,
)


def _format_error_payload(error: Exception) -> str:
    """Format one command CLI error as JSON.

    Args:
        error [Exception]: Error to render.

    Returns:
        str: JSON error payload.
    """
    payload: dict[str, object] = {"valid": False, "error": str(error)}
    error_payload: str = orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
    return error_payload


def _catalog_list_result(catalog: CommandCatalog) -> CommandCatalogListResult:
    """Build typed command catalog list output.

    Args:
        catalog [CommandCatalog]: Command catalog to render.

    Returns:
        CommandCatalogListResult: Typed list result.
    """
    entries: tuple[CommandCatalogEntry, ...] = tuple(
        CommandCatalogEntry(
            id=recipe.id,
            qualified_id=recipe.qualified_id,
            source=recipe.source,
            description=recipe.description,
            risk=recipe.risk,
            step_count=len(recipe.steps),
        )
        for recipe in catalog.commands
    )
    builtin_count: int = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.BUILTIN
    )
    repo_count: int = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.REPO
    )
    result = CommandCatalogListResult(
        commands=entries,
        builtin_count=builtin_count,
        repo_count=repo_count,
    )
    return result


def _format_catalog_human(entries: tuple[CommandCatalogEntry, ...]) -> str:
    """Format command catalog entries for humans.

    Args:
        entries [tuple[CommandCatalogEntry, ...]]: Entries to render.

    Returns:
        str: Human-readable catalog summary.
    """
    if not entries:
        empty_text: str = "No command recipes available."
        return empty_text

    lines: list[str] = [
        f"{entry.qualified_id}\t{entry.risk}\t{entry.step_count}\t{entry.description}"
        for entry in entries
    ]
    catalog_text: str = "\n".join(lines)
    return catalog_text


@commands_app.command("list")
def commands_list(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command config path override, relative to --cwd when not absolute.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed command catalog as JSON.",
    ),
) -> None:
    """List built-in and repo-defined command recipes.

    Args:
        cwd [Path]: Repository root used for config resolution.
        config_path [Path | None]: Optional config path override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        catalog: CommandCatalog = load_command_catalog(cwd=cwd, config_path=config_path)
        result: CommandCatalogListResult = _catalog_list_result(catalog)
    except (CommandRecipeLoadError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(_format_catalog_human(result.commands))


@commands_app.command("show")
def commands_show(
    command_id: str = typer.Argument(..., help="Qualified or unambiguous command id."),
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command config path override, relative to --cwd when not absolute.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed command recipe as JSON.",
    ),
) -> None:
    """Show one built-in or repo-defined command recipe.

    Args:
        command_id [str]: Qualified or unambiguous command id.
        cwd [Path]: Repository root used for config resolution.
        config_path [Path | None]: Optional config path override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        catalog: CommandCatalog = load_command_catalog(cwd=cwd, config_path=config_path)
        recipe: CommandRecipe = resolve_command_recipe(catalog, command_id)
        result = CommandShowResult(recipe=recipe)
    except (
        CommandCatalogResolutionError,
        CommandRecipeLoadError,
        ValidationError,
        ValueError,
    ) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    typer.echo(f"{result.recipe.qualified_id}: {result.recipe.description}")


@commands_app.command("validate")
def commands_validate(
    cwd: Path = typer.Option(
        Path("."),
        "--cwd",
        help="Repository root used to resolve .agent-remote.toml.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="Optional command config path override, relative to --cwd when not absolute.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the typed validation result as JSON.",
    ),
) -> None:
    """Validate built-in and repo-defined command recipes.

    Args:
        cwd [Path]: Repository root used for config resolution.
        config_path [Path | None]: Optional config path override.
        json_output [bool]: Whether to print JSON.
    """
    try:
        catalog: CommandCatalog = load_command_catalog(cwd=cwd, config_path=config_path)
        result = _catalog_list_result(catalog)
    except (CommandRecipeLoadError, ValidationError, ValueError) as error:
        if json_output:
            typer.echo(_format_error_payload(error))
        else:
            typer.echo(str(error))
        raise typer.Exit(code=2) from error

    if json_output:
        payload = {
            "valid": True,
            "command_count": len(result.commands),
            "builtin_count": result.builtin_count,
            "repo_count": result.repo_count,
        }
        typer.echo(orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode())
        return

    typer.echo("valid: True")
    typer.echo(f"command_count: {len(result.commands)}")
