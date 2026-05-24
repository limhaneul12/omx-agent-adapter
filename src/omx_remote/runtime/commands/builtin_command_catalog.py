from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandCatalog,
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)


def build_builtin_command_catalog() -> CommandCatalog:
    """Build the built-in project-owned command catalog.

    Returns:
        CommandCatalog: Built-in commands available without repo TOML.
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
                expected_artifacts=(".agent-remote/runs/review-diff/final-message.md",),
            ),
        ),
    )
    verify_handoff = CommandRecipe(
        id="verify-handoff",
        source=CommandSource.BUILTIN,
        description="Run repo verification gates and prepare a handoff artifact.",
        risk=CommandRisk.READ_ONLY,
        steps=(
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=("git", "diff", "--check"),
            ),
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=("uv", "run", "ruff", "check", "src", "tests"),
            ),
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=("uv", "run", "pyrefly", "check", "src"),
            ),
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=("uv", "run", "pytest", "-q"),
                expected_artifacts=(".agent-remote/runs/verify-handoff/handoff.md",),
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
    catalog = CommandCatalog(
        commands=(review_diff, verify_handoff, ultragoal_roadmap),
    )
    return catalog
