from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandCatalogEntry,
    CommandCatalogListResult,
)
from omx_remote.shared.omx_enums.command_enums import (
    CommandNamespace,
    CommandRecipeCategory,
    CommandSource,
)


def _catalog_entries(catalog: CommandCatalog) -> tuple[CommandCatalogEntry, ...]:
    """Build list entries from the command catalog.

    Args:
        catalog [CommandCatalog]: Loaded command catalog.

    Returns:
        tuple[CommandCatalogEntry, ...]: Public command list entries.
    """
    entries: tuple[CommandCatalogEntry, ...] = tuple(
        CommandCatalogEntry(
            id=recipe.display_id,
            qualified_id=recipe.display_qualified_id,
            machine_id=recipe.public_id,
            machine_qualified_id=recipe.qualified_id,
            source=recipe.source,
            namespace=recipe.namespace,
            category=recipe.category,
            description=recipe.description,
            risk=recipe.risk,
            step_count=len(recipe.steps),
        )
        for recipe in catalog.commands
    )
    return entries


def catalog_list_result(catalog: CommandCatalog) -> CommandCatalogListResult:
    """Build typed command catalog list output.

    Args:
        catalog [CommandCatalog]: Loaded command catalog.

    Returns:
        CommandCatalogListResult: List result contract.
    """
    builtin_count: int = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.BUILTIN
    )
    repo_count: int = sum(
        1 for recipe in catalog.commands if recipe.source == CommandSource.REPO
    )
    public_workflow_commands: int = sum(
        1
        for recipe in catalog.commands
        if recipe.namespace == CommandNamespace.WORKFLOW
        and recipe.category
        in {
            CommandRecipeCategory.LIFECYCLE,
            CommandRecipeCategory.MACRO,
        }
        and recipe.source == CommandSource.BUILTIN
    )
    lifecycle_commands: int = sum(
        1
        for recipe in catalog.commands
        if recipe.category == CommandRecipeCategory.LIFECYCLE
    )
    macro_commands: int = sum(
        1
        for recipe in catalog.commands
        if recipe.category == CommandRecipeCategory.MACRO
    )
    adapter_ops_commands: int = sum(
        1
        for recipe in catalog.commands
        if recipe.namespace == CommandNamespace.ADAPTER_OPS
    )
    result = CommandCatalogListResult(
        commands=_catalog_entries(catalog),
        builtin_count=builtin_count,
        repo_count=repo_count,
        public_workflow_commands=public_workflow_commands,
        lifecycle_commands=lifecycle_commands,
        macro_commands=macro_commands,
        adapter_ops_commands=adapter_ops_commands,
    )
    return result
