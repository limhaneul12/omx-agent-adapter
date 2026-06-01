from omx_remote.runtime.commands.catalog.workflow_command_catalog import (
    build_workflow_command_catalog,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandCatalog


def build_builtin_command_catalog() -> CommandCatalog:
    """Build the built-in project-owned command catalog.

    Returns:
        CommandCatalog: Built-in commands available without repo TOML.
    """
    catalog = CommandCatalog(commands=build_workflow_command_catalog())
    return catalog
