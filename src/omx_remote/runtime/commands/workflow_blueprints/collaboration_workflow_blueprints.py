from omx_remote.runtime.commands.workflow_blueprints.collaboration_kickoff_blueprint import (
    build_collaboration_kickoff_recipe,
)
from omx_remote.runtime.commands.workflow_blueprints.conflict_resolution_council_blueprint import (
    build_conflict_resolution_council_recipe,
)
from omx_remote.runtime.commands.workflow_blueprints.integration_room_blueprint import (
    build_integration_room_recipe,
)
from omx_remote.runtime.commands.workflow_blueprints.parallel_review_board_blueprint import (
    build_parallel_review_board_recipe,
)
from omx_remote.runtime.commands.workflow_blueprints.release_readiness_room_blueprint import (
    build_release_readiness_room_recipe,
)
from omx_remote.runtime.commands.workflow_blueprints.team_standup_sync_blueprint import (
    build_team_standup_sync_recipe,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandRecipe


def build_collaboration_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build collaboration, review, and release workflow recipes.

    Returns:
        tuple[CommandRecipe, ...]: Built-in collaboration workflow recipes.
    """
    recipes = (
        build_collaboration_kickoff_recipe(),
        build_team_standup_sync_recipe(),
        build_integration_room_recipe(),
        build_conflict_resolution_council_recipe(),
        build_parallel_review_board_recipe(),
        build_release_readiness_room_recipe(),
    )
    return recipes
