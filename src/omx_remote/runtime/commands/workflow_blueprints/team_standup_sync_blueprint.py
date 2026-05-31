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


def build_team_standup_sync_recipe() -> CommandRecipe:
    """Build the Team standup sync workflow recipe.

    Returns:
        CommandRecipe: Team standup sync recipe.
    """
    recipe = CommandRecipe(
        id="team-standup-sync",
        source=CommandSource.BUILTIN,
        description=(
            "Read active/recent OMX Team evidence and summarize workers, blockers, "
            "proof layers, and suggested dispatches without mutating mailboxes."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("agent-remote", "team", "status", "--team", "<task>")),
            local_step(("agent-remote", "team", "tasks", "--team", "<task>")),
            local_step(("agent-remote", "team", "events", "--team", "<task>")),
            codex_step(
                "Team standup sync for team or task: <task>. Use role-separated "
                "sections for status_analyst, blocker_triage, and dispatch_planner. "
                "Summarize runtime_status, worker_summary, proof_layers, "
                "blocked_workers, missing_evidence, suggested_dispatches, "
                "suggested_wait_or_integrate_decision, and next_command. If worker "
                "status or admin-report evidence is absent, mark it as missing "
                "evidence instead of inventing it. Suggest mailbox commands only; "
                "do not mutate Team state.",
                output_last_message=(
                    ".agent-remote/runs/team-standup-sync/<slug>_standup_report.md"
                ),
            ),
            prompt_step(
                "Dispatch suggestion handoff only. Review the standup report before "
                "sending any worker mailbox messages, launching new workers, or "
                "transitioning Team tasks.",
                expected_artifacts=(
                    ".agent-remote/runs/team-standup-sync/"
                    "<slug>_suggested_dispatches.md",
                ),
            ),
        ),
    )
    return recipe
