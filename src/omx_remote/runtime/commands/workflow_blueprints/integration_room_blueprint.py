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


def build_integration_room_recipe() -> CommandRecipe:
    """Build the integration room workflow recipe.

    Returns:
        CommandRecipe: Integration room recipe.
    """
    recipe = CommandRecipe(
        id="integration-room",
        source=CommandSource.BUILTIN,
        description=(
            "Integrate Team/subagent/run outputs into accepted decisions, conflict "
            "matrix, integration order, and verification plan."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            local_step(("agent-remote", "runs", "list", "--cwd", ".", "--json")),
            codex_step(
                "Integration room for: <task>. Use role-separated sections for "
                "integrator, architect, test_reviewer, critic, and synthesizer. "
                "Inspect available run ledger and Team/subagent evidence. Produce "
                "inputs_reviewed, accepted_outputs, rejected_outputs, conflicts, "
                "missing_evidence, integration_order, verification_plan, and "
                "recommended_next_command.",
                output_last_message=(
                    ".agent-remote/runs/integration-room/<slug>_integration_report.md"
                ),
            ),
            codex_step(
                "Create a verification plan for integrating the accepted outputs for "
                "<task>. Include tests, type checks, review-board lanes, QA war-room "
                "candidates, rollback points, and evidence required before approval.",
                output_last_message=(
                    ".agent-remote/runs/integration-room/<slug>_verification_plan.md"
                ),
            ),
            prompt_step(
                "Integration handoff only. Apply no patches until accepted outputs, "
                "conflicts, and verification plan have been reviewed by the current "
                "agent.",
                expected_artifacts=(
                    ".agent-remote/runs/integration-room/<slug>_conflict_matrix.md",
                    ".agent-remote/runs/integration-room/"
                    "<slug>_accepted_output_ledger.md",
                    ".agent-remote/runs/integration-room/<slug>_next_patch_plan.md",
                ),
            ),
        ),
    )
    return recipe
