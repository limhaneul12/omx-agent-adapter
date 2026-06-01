from omx_remote.runtime.commands.blueprints.adapter_ops_blueprints import (
    build_adapter_ops_blueprints,
)
from omx_remote.runtime.commands.blueprints.consolidated_lifecycle_blueprints import (
    build_public_workflow_blueprints,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandRecipe


def build_workflow_command_catalog() -> tuple[CommandRecipe, ...]:
    """Build project-owned workflow and maintenance recipes.

    Returns:
        tuple[CommandRecipe, ...]: Built-in command recipes.
    """
    recipes = (
        *build_public_workflow_blueprints(),
        *build_adapter_ops_blueprints(),
    )
    return recipes
