from omx_remote.runtime.commands.blueprints.company_run_blueprint import (
    build_company_run_blueprint,
)
from omx_remote.runtime.commands.blueprints.public_workflow_lifecycle_recipes import (
    _discovery_gate_recipe,
    _idea_to_prd_recipe,
    _implementation_kickoff_recipe,
    _research_brief_recipe,
    _route_next_recipe,
)
from omx_remote.runtime.commands.blueprints.public_workflow_review_recipes import (
    _integration_plan_recipe,
    _release_readiness_recipe,
    _review_gate_recipe,
    _team_sync_recipe,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandRecipe

PUBLIC_WORKFLOW_COMMAND_IDS: tuple[str, ...] = (
    "route-next",
    "discovery-gate",
    "research-brief",
    "idea-to-prd",
    "implementation-kickoff",
    "team-sync",
    "integration-plan",
    "review-gate",
    "release-readiness",
    "company-run",
)


def build_public_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build the 10 public workflow recipes.

    Returns:
        tuple[CommandRecipe, ...]: Public workflow recipes.
    """
    recipes = (
        _route_next_recipe(),
        _discovery_gate_recipe(),
        _research_brief_recipe(),
        _idea_to_prd_recipe(),
        _implementation_kickoff_recipe(),
        _team_sync_recipe(),
        _integration_plan_recipe(),
        _review_gate_recipe(),
        _release_readiness_recipe(),
        build_company_run_blueprint(),
    )
    return recipes
