from pathlib import Path

from pydantic import ValidationError

from omx_remote.runtime.commands.command_catalog_resolver import load_command_catalog
from omx_remote.runtime.commands.command_recipe_loader import CommandRecipeLoadError
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitCommandRecipeSummary,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandSource,
)


def summarize_cockpit_command_recipes(cwd: str | Path) -> CockpitCommandRecipeSummary:
    """Summarize command recipes for cockpit snapshots.

    Args:
        cwd [str | Path]: Repository root used to resolve `.agent-remote.toml`.

    Returns:
        CockpitCommandRecipeSummary: Recipe counts and warnings.
    """
    try:
        catalog: CommandCatalog = load_command_catalog(cwd=cwd)
    except (CommandRecipeLoadError, ValidationError) as error:
        summary = CockpitCommandRecipeSummary(
            available_count=0,
            builtin_count=0,
            repo_count=0,
            qualified_ids=(),
            warnings=(f"Command recipes could not be loaded: {error}",),
        )
        return summary

    qualified_ids: tuple[str, ...] = tuple(recipe.qualified_id for recipe in catalog.commands)
    builtin_count: int = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.BUILTIN
    )
    repo_count: int = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.REPO
    )
    summary = CockpitCommandRecipeSummary(
        available_count=len(catalog.commands),
        builtin_count=builtin_count,
        repo_count=repo_count,
        qualified_ids=qualified_ids,
        warnings=(),
    )
    return summary
