from omx_remote.runtime.commands.workflow_command_catalog import (
    build_workflow_command_catalog,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)


def _core_builtin_recipes() -> tuple[CommandRecipe, ...]:
    """Build the core built-in project command recipes.

    Returns:
        tuple[CommandRecipe, ...]: Core recipes available without repo TOML.
    """
    review_diff = CommandRecipe(
        id="review-diff",
        source=CommandSource.BUILTIN,
        description="Review the current git diff against repository rules.",
        risk=CommandRisk.READ_ONLY,
        steps=(
            CommandStep(
                command=CommandStepCommand.CODEX_EXEC,
                inline_prompt=(
                    "Review the current git diff against the repository rules. "
                    "Return findings, risks, and an approval recommendation."
                ),
                output_last_message=".agent-remote/runs/review-diff/final-message.md",
            ),
        ),
    )
    ultragoal_roadmap = CommandRecipe(
        id="ultragoal-roadmap",
        source=CommandSource.BUILTIN,
        description="Plan an OMX UltraGoal run from a roadmap brief file.",
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt="Use omx ultragoal create-goals with the selected roadmap brief.",
            ),
        ),
    )
    recipes = (
        review_diff,
        ultragoal_roadmap,
    )
    return recipes


def build_builtin_command_catalog() -> CommandCatalog:
    """Build the built-in project-owned command catalog.

    Returns:
        CommandCatalog: Built-in commands available without repo TOML.
    """
    catalog = CommandCatalog(
        commands=(
            *_core_builtin_recipes(),
            *build_workflow_command_catalog(),
        ),
    )
    return catalog
