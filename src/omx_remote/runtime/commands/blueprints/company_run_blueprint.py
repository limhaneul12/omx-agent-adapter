from omx_remote.runtime.commands.blueprints.recipe_blueprint_factories import (
    codex_step,
    role_lane,
)
from omx_remote.runtime.prompt_assets import prompt_asset_path
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandNamespace,
    CommandRecipe,
    CommandRecipeCategory,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_role_schemas import CommandRoleExecution


def build_company_run_blueprint() -> CommandRecipe:
    """Build the company-run macro orchestration recipe.

    Returns:
        CommandRecipe: Company-run recipe.
    """
    run_root = ".comx-agent/runs/company-run"
    recipe = CommandRecipe(
        id="company-run",
        source=CommandSource.BUILTIN,
        description=(
            "Run a build-oriented company-style macro loop with discovery/ROI "
            "gates, internal governance, Team, subagents, review, release, and "
            "Alexandria MCP tool points."
        ),
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.MACRO,
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            codex_step(
                "Plan company-run macro orchestration for: <task>.",
                agent="route_strategist",
                prompt_file=prompt_asset_path(
                    "company-run", "company-run-orchestration.md"
                ),
                output_last_message=f"{run_root}/company-run-plan.md",
                expected_artifacts=(
                    f"{run_root}/memory-recall.md",
                    f"{run_root}/discovery/discovery-decision-packet.json",
                    f"{run_root}/discovery/discovery-summary.md",
                    f"{run_root}/discovery/roi-no-build-gate.json",
                    f"{run_root}/discovery/deep-interview-handoff.md",
                    f"{run_root}/decisions/discovery-decision-report.md",
                    f"{run_root}/research-vote.md",
                    f"{run_root}/proceed-vote.md",
                    f"{run_root}/prd-readiness.md",
                    f"{run_root}/team-plan.md",
                    f"{run_root}/review-loop.md",
                    f"{run_root}/release-closeout.md",
                ),
                role_lanes=(
                    role_lane(
                        lane_id="company_orchestrator",
                        execution=CommandRoleExecution.SYNTHESIS,
                        purpose="Own phase sequencing, discovery/ROI gates, internal decisions, and closeout.",
                        artifact=f"{run_root}/company-run-plan.md",
                        approval_required=True,
                    ),
                    role_lane(
                        lane_id="discovery_gate",
                        execution=CommandRoleExecution.VALIDATION_GATE,
                        purpose="Run Gate 0 discovery, ROI/no-build, and deep-interview handoff before expensive work.",
                        artifact=f"{run_root}/discovery/discovery-decision-packet.json",
                        approval_required=True,
                    ),
                    role_lane(
                        lane_id="research_council",
                        execution=CommandRoleExecution.CODEX_SUBAGENT,
                        purpose="Run independent research lanes and internal research decision record.",
                        artifact=f"{run_root}/research-vote.md",
                    ),
                    role_lane(
                        lane_id="executive_council",
                        execution=CommandRoleExecution.VALIDATION_GATE,
                        purpose="Review PRD/test spec before implementation-kickoff.",
                        artifact=f"{run_root}/prd-readiness.md",
                        approval_required=True,
                    ),
                    role_lane(
                        lane_id="omx_team",
                        execution=CommandRoleExecution.OMX_TEAM,
                        purpose="Durable implementation fanout after implementation-kickoff.",
                        artifact=f"{run_root}/team-plan.md",
                        approval_required=True,
                    ),
                    role_lane(
                        lane_id="alexandria_mcp",
                        execution=CommandRoleExecution.ALEXANDRIA_MEMORY,
                        purpose="Use Alexandria MCP tools for memory recall, librarian queries, curation, and closeout.",
                        artifact=f"{run_root}/memory-recall.md",
                    ),
                ),
            ),
            CommandStep(
                command=CommandStepCommand.OMX_TEAM,
                inline_prompt=(
                    "Policy-gated company-run Team handoff. Team and subagents are "
                    "required only after discovery/ROI, research/proceed decisions, and PRD/test spec readiness."
                ),
                expected_artifacts=(f"{run_root}/team-plan.md",),
            ),
        ),
    )
    return recipe
