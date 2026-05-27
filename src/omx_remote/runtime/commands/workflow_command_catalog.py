from omx_remote.runtime.commands.company_workflow_blueprints import (
    build_company_workflow_blueprints,
)
from omx_remote.runtime.commands.operations_workflow_blueprints import (
    build_operations_workflow_blueprints,
)
from omx_remote.runtime.commands.research_workflow_blueprints import (
    build_research_workflow_blueprints,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandRecipe


def build_workflow_command_catalog() -> tuple[CommandRecipe, ...]:
    """Build all built-in project-owned workflow recipes.

    Returns:
        See function return annotation."""
    recipes = (
        *build_research_workflow_blueprints(),
        *build_company_workflow_blueprints(),
        *build_operations_workflow_blueprints(),
    )
    return recipes
