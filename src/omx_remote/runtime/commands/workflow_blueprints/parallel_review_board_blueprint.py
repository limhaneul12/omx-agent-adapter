from omx_remote.runtime.commands.command_blueprint_helpers import (
    codex_step,
    local_step,
    prompt_step,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
)


def build_parallel_review_board_recipe() -> CommandRecipe:
    """Build the parallel review board workflow recipe.

    Returns:
        CommandRecipe: Parallel review board recipe.
    """
    recipe = CommandRecipe(
        id="parallel-review-board",
        source=CommandSource.BUILTIN,
        description=(
            "Run specialist review lanes for security, tests, maintainability, "
            "performance, docs, and final approve/block synthesis."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            local_step(("git", "diff", "--check")),
            local_step(("git", "diff", "--name-only")),
            codex_step(
                "Parallel review board for: <task>. Spawn or simulate read-only "
                "specialist lanes: security, tests, maintainability, performance, "
                "docs, and final reviewer. Require concrete file references, "
                "severity, confidence, false_positive_risks, verification_commands, "
                "and approve_block_verdict. Do not modify files.",
                output_last_message=(
                    ".agent-remote/runs/parallel-review-board/<slug>_review_verdict.md"
                ),
            ),
            prompt_step(
                "Review-board evidence handoff. Keep role findings separate and do "
                "not claim approval if any blocker lacks verification evidence.",
                expected_artifacts=(
                    ".agent-remote/runs/parallel-review-board/<slug>_security.md",
                    ".agent-remote/runs/parallel-review-board/<slug>_tests.md",
                    ".agent-remote/runs/parallel-review-board/"
                    "<slug>_maintainability.md",
                    ".agent-remote/runs/parallel-review-board/<slug>_performance.md",
                    ".agent-remote/runs/parallel-review-board/<slug>_docs.md",
                ),
            ),
        ),
    )
    return recipe
