from pathlib import Path

from omx_remote.runtime.commands.catalog.builtin_command_catalog import (
    build_builtin_command_catalog,
)
from omx_remote.runtime.commands.catalog.command_recipe_loader import (
    load_repo_command_recipes,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandRecipe,
)
from omx_remote.shared.omx_enums.command_enums import CommandSource


class CommandCatalogResolutionError(ValueError):
    """Raised when a command id cannot be resolved safely."""


_SOURCE_PREFIXES: frozenset[str] = frozenset(source.value for source in CommandSource)


def _clean_command_id(command_id: str) -> str:
    """Strip caller whitespace without accepting alternate command spellings.

    Args:
        command_id [str]: Caller-supplied command id.

    Returns:
        str: Cleaned command id text.
    """
    cleaned_id: str = command_id.strip()
    return cleaned_id


def _source_and_catalog_id(command_id: str) -> tuple[str | None, str]:
    """Split only known source prefixes from a command id.

    Args:
        command_id [str]: Caller-supplied command id.

    Returns:
        tuple[str | None, str]: Optional source prefix and catalog id.
    """
    if ":" not in command_id:
        return None, command_id
    prefix, suffix = command_id.split(":", maxsplit=1)
    if prefix in _SOURCE_PREFIXES:
        return prefix, suffix
    return None, command_id


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
    normalized_id: str = _clean_command_id(command_id)
    source_prefix, _ = _source_and_catalog_id(normalized_id)
    if source_prefix is not None:
        recipe = catalog.find(normalized_id)
        if recipe is None:
            raise CommandCatalogResolutionError(
                f"No command named {command_id} was found."
            )
        return recipe

    matches: tuple[CommandRecipe, ...] = tuple(
        recipe for recipe in catalog.commands if recipe.matches_id(normalized_id)
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
