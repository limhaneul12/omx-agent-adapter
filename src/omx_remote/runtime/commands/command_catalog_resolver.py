from pathlib import Path

from omx_remote.runtime.commands.builtin_command_catalog import (
    build_builtin_command_catalog,
)
from omx_remote.runtime.commands.command_recipe_loader import load_repo_command_recipes
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandRecipe,
)


class CommandCatalogResolutionError(ValueError):
    """Raised when a command id cannot be resolved safely."""


def load_command_catalog(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> CommandCatalog:
    """Load built-in and repo-defined command recipes.

    Args:
        cwd [str | Path | None]: Base working directory for repo config.
        config_path [str | Path | None]: Optional repo config override.

    Returns:
        CommandCatalog: Merged command catalog.
    """
    builtin_catalog: CommandCatalog = build_builtin_command_catalog()
    repo_recipes: tuple[CommandRecipe, ...] = load_repo_command_recipes(
        cwd=cwd,
        config_path=config_path,
    )
    catalog = CommandCatalog(
        commands=(*builtin_catalog.commands, *repo_recipes),
    )
    return catalog


def resolve_command_recipe(catalog: CommandCatalog, command_id: str) -> CommandRecipe:
    """Resolve one command id, requiring explicit source when ambiguous.

    Args:
        catalog [CommandCatalog]: Command catalog to search.
        command_id [str]: Qualified or short command id.

    Returns:
        CommandRecipe: Resolved command recipe.
    """
    if ":" in command_id:
        recipe = catalog.find(command_id)
        if recipe is None:
            raise CommandCatalogResolutionError(
                f"No command named {command_id} was found."
            )
        return recipe

    matches: tuple[CommandRecipe, ...] = tuple(
        recipe for recipe in catalog.commands if recipe.id == command_id
    )
    if len(matches) == 1:
        resolved_recipe: CommandRecipe = matches[0]
        return resolved_recipe
    if not matches:
        raise CommandCatalogResolutionError(f"No command named {command_id} was found.")

    qualified_ids: str = ", ".join(recipe.qualified_id for recipe in matches)
    raise CommandCatalogResolutionError(
        f"Command id {command_id} is ambiguous; choose one of: {qualified_ids}."
    )
