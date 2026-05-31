from pathlib import Path

from omx_remote.runtime.commands.command_blueprint_helpers import (
    codex_step,
    local_step,
    role_lane,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_role_schemas import CommandRoleExecution

_PROMPT_ROOT = str(
    Path(__file__).resolve().parents[1] / "prompting" / "collaboration_kickoff"
)
_COLLAB_RUN_ROOT = ".agent-remote/runs/collaboration-kickoff/<dated-workspace>"
_COUNCIL_ROOT = f"{_COLLAB_RUN_ROOT}/03_council"
_ULTRAGOAL_ROOT = f"{_COLLAB_RUN_ROOT}/04_ultragoal"
_RUNTIME_ROOT = f"{_COLLAB_RUN_ROOT}/05_runtime"


def build_collaboration_kickoff_recipe() -> CommandRecipe:
    """Build the collaboration kickoff workflow recipe.

    Returns:
        CommandRecipe: Collaboration kickoff recipe.
    """
    context_path = f"{_COUNCIL_ROOT}/context_research.md"
    architecture_path = f"{_COUNCIL_ROOT}/architecture_route.md"
    critique_path = f"{_COUNCIL_ROOT}/risk_critique.md"
    team_plan_path = f"{_COUNCIL_ROOT}/team_fanout_plan.md"
    plan_path = f"{_COUNCIL_ROOT}/collaboration_plan.md"
    story_preview_path = f"{_ULTRAGOAL_ROOT}/ultragoal_story_preview.md"
    team_handoff_path = f"{_RUNTIME_ROOT}/team_handoff.md"
    recipe = CommandRecipe(
        id="collaboration-kickoff",
        source=CommandSource.BUILTIN,
        description=(
            "Turn a broad objective into a real collaboration plan with explicit "
            "Codex native-agent lanes, Team fanout advice, UltraGoal story preview, "
            "and policy-gated runtime handoff."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            local_step(
                ("agent-remote", "cockpit", "snapshot", "--cwd", ".", "--json"),
                role_lanes=(
                    role_lane(
                        "cockpit_evidence",
                        CommandRoleExecution.LOCAL_EVIDENCE,
                        "Collect local capability and runtime evidence before routing.",
                    ),
                ),
            ),
            local_step(
                (
                    "agent-remote",
                    "next",
                    "--cwd",
                    ".",
                    "--task",
                    "<task>",
                    "--json",
                ),
                role_lanes=(
                    role_lane(
                        "next_action_reader",
                        CommandRoleExecution.LOCAL_EVIDENCE,
                        "Read adapter next-action evidence before planning collaboration.",
                    ),
                ),
            ),
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
                ),
                role_lanes=(
                    role_lane(
                        "route_planner",
                        CommandRoleExecution.LOCAL_EVIDENCE,
                        "Collect route recommendation evidence before team/subagent planning.",
                    ),
                ),
            ),
            codex_step(
                "As the researcher native agent, map current context, unknowns, and "
                "evidence gaps for collaboration kickoff task: <task>.",
                agent="researcher",
                prompt_file=f"{_PROMPT_ROOT}/role_council.md",
                output_last_message=context_path,
                role_lanes=(
                    role_lane(
                        "researcher",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Map current context, unknowns, and evidence gaps.",
                        context_path,
                    ),
                ),
            ),
            codex_step(
                "As the architect native agent, choose boundaries, route, integration "
                "shape, and safe decomposition for collaboration kickoff task: <task>.",
                agent="architect",
                prompt_file=f"{_PROMPT_ROOT}/role_council.md",
                output_last_message=architecture_path,
                role_lanes=(
                    role_lane(
                        "architect",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Choose boundaries, route, and integration shape.",
                        architecture_path,
                        approval_required=True,
                    ),
                ),
            ),
            codex_step(
                "As the critic native agent, challenge risks, hidden assumptions, "
                "over-orchestration, and missing evidence for collaboration task: <task>.",
                agent="critic",
                prompt_file=f"{_PROMPT_ROOT}/role_council.md",
                output_last_message=critique_path,
                role_lanes=(
                    role_lane(
                        "critic",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Challenge risks, hidden assumptions, and over-orchestration.",
                        critique_path,
                        approval_required=True,
                    ),
                ),
            ),
            codex_step(
                "As the team-executor native agent, decide whether OMX Team fanout is "
                "warranted and safe for collaboration task: <task>. Include worker "
                "ownership, worktree boundaries, mailbox protocol, and stop conditions.",
                agent="team-executor",
                prompt_file=f"{_PROMPT_ROOT}/team_handoff.md",
                output_last_message=team_plan_path,
                role_lanes=(
                    role_lane(
                        "team_planner",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Decide whether OMX Team fanout is warranted and safe.",
                        team_plan_path,
                    ),
                ),
            ),
            codex_step(
                "As the synthesizer native agent, combine context, architecture, critic, "
                "and Team fanout artifacts for: <task>. Produce objective, "
                "recommended_route, rejected_routes, subagent_roles, team_fanout_needed, "
                "ultragoal_recommended, preflight_commands, dry_run_commands, "
                "mutation_blockers, and next_command.",
                agent="planner",
                prompt_file=f"{_PROMPT_ROOT}/role_council.md",
                output_last_message=plan_path,
                role_lanes=(
                    role_lane(
                        "synthesizer",
                        CommandRoleExecution.SYNTHESIS,
                        "Produce one route and next command from all role evidence.",
                        plan_path,
                    ),
                ),
            ),
            codex_step(
                "As the ultragoal_story_planner native agent, draft candidate UltraGoal "
                "stories and Team fanout lanes for: <task> only if the collaboration plan "
                "justifies durable execution. Include acceptance criteria, verification "
                "commands, worktree boundaries, subagent review roles, and stop conditions.",
                agent="planner",
                prompt_file=f"{_PROMPT_ROOT}/team_handoff.md",
                output_last_message=story_preview_path,
                role_lanes=(
                    role_lane(
                        "ultragoal_story_planner",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Draft UltraGoal story candidates and verification gates.",
                        story_preview_path,
                    ),
                    role_lane(
                        "team_fanout_planner",
                        CommandRoleExecution.OMX_TEAM,
                        "Draft Team lanes, worker ownership, and mailbox protocol.",
                        team_handoff_path,
                    ),
                ),
            ),
            CommandStep(
                command=CommandStepCommand.OMX_TEAM,
                inline_prompt=(
                    "Policy-gated Team handoff for collaboration-kickoff. Use the "
                    "collaboration plan and story preview to decide whether the next "
                    "explicit command should be idea-to-prd-council, team-sprint-plan, "
                    "omx ultragoal create-goals, or an OMX Team launch inside an active "
                    "UltraGoal story. Do not silently launch Team from preview."
                ),
                expected_artifacts=(team_handoff_path,),
                role_lanes=(
                    role_lane(
                        "team_runtime_handoff",
                        CommandRoleExecution.RUNTIME_HANDOFF,
                        "Prepare explicit Team launch handoff after agent approval.",
                        team_handoff_path,
                        approval_required=True,
                    ),
                ),
            ),
        ),
    )
    return recipe
