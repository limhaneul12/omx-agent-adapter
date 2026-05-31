from omx_remote.runtime.commands.command_blueprint_helpers import (
    codex_step,
    local_step,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
)


def build_conflict_resolution_council_recipe() -> CommandRecipe:
    """Build the conflict resolution council workflow recipe.

    Returns:
        CommandRecipe: Conflict resolution council recipe.
    """
    recipe = CommandRecipe(
        id="conflict-resolution-council",
        source=CommandSource.BUILTIN,
        description=(
            "Resolve conflicting agent outputs or design options with an ADR-style "
            "decision and explicit reversibility/risk notes."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            local_step(("agent-remote", "cockpit", "snapshot", "--cwd", ".", "--json")),
            local_step(
                (
                    "agent-remote",
                    "route",
                    "recommend",
                    "--cwd",
                    ".",
                    "--task",
                    "<task>",
                    "--json",
                )
            ),
            codex_step(
                "Conflict resolution council for: <task>. Use role-separated "
                "sections for proposer, opposer, architect_judge, risk_critic, "
                "and final_arbiter. Produce decision_question, options_considered, "
                "decision_drivers, chosen_option, rejected_options, reversibility, "
                "risks, follow_up_experiments, confidence, and next_command. "
                "Separate evidence from inference.",
                output_last_message=(
                    ".agent-remote/runs/conflict-resolution-council/"
                    "<slug>_adr_decision.md"
                ),
            ),
        ),
    )
    return recipe
