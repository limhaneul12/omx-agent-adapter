from omx_remote.runtime.commands.blueprints.recipe_blueprint_factories import (
    codex_step,
    local_step,
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


def _route_next_recipe() -> CommandRecipe:
    """Build the route-next lifecycle recipe.

    Returns:
        CommandRecipe: Route-next recipe.
    """
    report_path = ".comx-agent/runs/route-next/route-recommendation.md"
    recipe = CommandRecipe(
        id="route-next",
        source=CommandSource.BUILTIN,
        description="Classify a task and recommend the safest next command or runtime lane.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("comx-agent", "cockpit", "snapshot", "--cwd", ".", "--json")),
            local_step(
                (
                    "comx-agent",
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
                "Produce the route-next recommendation for: <task>.",
                agent="route_strategist",
                prompt_file=prompt_asset_path("route-next", "route-next-plan.md"),
                output_last_message=report_path,
                role_lanes=(
                    role_lane(
                        "route_strategist",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Classify the task and recommend the safest next command.",
                        report_path,
                    ),
                ),
            ),
        ),
    )
    return recipe


def _discovery_gate_recipe() -> CommandRecipe:
    """Build the discovery-gate lifecycle recipe.

    Returns:
        CommandRecipe: Discovery-gate recipe.
    """
    run_root = ".comx-agent/runs/discovery-gate"
    recipe = CommandRecipe(
        id="discovery-gate",
        source=CommandSource.BUILTIN,
        description=(
            "Clarify vague ideas, score ambiguity, decide no-build/reroute/research/"
            "PRD/company-run readiness, and bridge to OMX deep-interview when needed."
        ),
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Produce the discovery-gate decision packet for: <task>.",
                agent="route_strategist",
                prompt_file=prompt_asset_path("discovery-gate", "discovery-gate.md"),
                output_last_message=f"{run_root}/discovery-summary.md",
                expected_artifacts=(
                    f"{run_root}/discovery-decision-packet.json",
                    f"{run_root}/discovery-summary.md",
                    f"{run_root}/ambiguity-score.json",
                    f"{run_root}/interview-handoff.md",
                    f"{run_root}/interview-transcript-reference.json",
                ),
                role_lanes=(
                    role_lane(
                        "discovery_gatekeeper",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Build the typed Discovery Decision Packet and routing verdict.",
                        f"{run_root}/discovery-decision-packet.json",
                    ),
                    role_lane(
                        "deep_interview_bridge",
                        CommandRoleExecution.RUNTIME_HANDOFF,
                        "Create an OMX deep-interview handoff only when ambiguity remains.",
                        f"{run_root}/interview-handoff.md",
                        approval_required=True,
                    ),
                    role_lane(
                        "roi_no_build_gate",
                        CommandRoleExecution.VALIDATION_GATE,
                        "Challenge company-run ROI and cheaper/no-build alternatives.",
                        f"{run_root}/ambiguity-score.json",
                        approval_required=True,
                    ),
                ),
            ),
        ),
    )
    return recipe


def _research_brief_recipe() -> CommandRecipe:
    """Build the research-brief lifecycle recipe.

    Returns:
        CommandRecipe: Research-brief recipe.
    """
    brief_path = ".comx-agent/runs/research-brief/evidence-brief.md"
    recipe = CommandRecipe(
        id="research-brief",
        source=CommandSource.BUILTIN,
        description="Produce a source-backed evidence brief with confidence and uncertainty labels.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.EXTERNAL_NETWORK,
        steps=(
            codex_step(
                "Build the research-brief evidence synthesis for: <task>.",
                agent="research_analyst",
                prompt_file=prompt_asset_path(
                    "research-brief", "research-brief-plan.md"
                ),
                output_last_message=brief_path,
                search=True,
                role_lanes=(
                    role_lane(
                        "research_analyst",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Gather source-backed facts, inferences, and uncertainty labels.",
                        brief_path,
                    ),
                    role_lane(
                        "evidence_critic",
                        CommandRoleExecution.VALIDATION_GATE,
                        "Challenge source quality and identify remaining unknowns.",
                        ".comx-agent/runs/research-brief/evidence-critic.md",
                    ),
                ),
            ),
        ),
    )
    return recipe


def _idea_to_prd_recipe() -> CommandRecipe:
    """Build the idea-to-prd lifecycle recipe.

    Returns:
        CommandRecipe: Idea-to-PRD recipe.
    """
    prd_root = ".comx-agent/runs/idea-to-prd"
    recipe = CommandRecipe(
        id="idea-to-prd",
        source=CommandSource.BUILTIN,
        description="Convert an idea and evidence into PRD, test spec, and execution brief artifacts.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Create PRD, test spec, and execution brief for: <task>.",
                agent="research_analyst",
                prompt_file=prompt_asset_path("idea-to-prd", "idea-to-prd-plan.md"),
                output_last_message=f"{prd_root}/prd.md",
                expected_artifacts=(
                    f"{prd_root}/prd.md",
                    f"{prd_root}/test-spec.md",
                    f"{prd_root}/execution-brief.md",
                    f"{prd_root}/risks-and-decisions.md",
                ),
                role_lanes=(
                    role_lane(
                        "product_prd_writer",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Write PRD, test spec, execution brief, and risk notes.",
                        f"{prd_root}/prd.md",
                    ),
                    role_lane(
                        "planning_validation_gate",
                        CommandRoleExecution.VALIDATION_GATE,
                        "Decide whether implementation-kickoff is ready or blocked.",
                        f"{prd_root}/readiness-verdict.md",
                        approval_required=True,
                    ),
                ),
            ),
        ),
    )
    return recipe


def _implementation_kickoff_recipe() -> CommandRecipe:
    """Build the implementation-kickoff lifecycle recipe.

    Returns:
        CommandRecipe: Implementation-kickoff recipe.
    """
    run_root = ".comx-agent/runs/implementation-kickoff"
    recipe = CommandRecipe(
        id="implementation-kickoff",
        source=CommandSource.BUILTIN,
        description="Turn accepted planning artifacts into a policy-gated development handoff.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            codex_step(
                "Prepare the implementation-kickoff development-start gate for: <task>.",
                agent="implementation_architect",
                prompt_file=prompt_asset_path(
                    "implementation-kickoff",
                    "implementation-kickoff-plan.md",
                ),
                output_last_message=f"{run_root}/handoff.md",
                expected_artifacts=(
                    f"{run_root}/owner-lanes.md",
                    f"{run_root}/verification-commands.md",
                    f"{run_root}/rollback-points.md",
                    f"{run_root}/runtime-handoff.md",
                ),
                role_lanes=(
                    role_lane(
                        "implementation_architect",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Define owner lanes, runtime handoff, verification, and rollback.",
                        f"{run_root}/handoff.md",
                    ),
                    role_lane(
                        "team_runtime_handoff",
                        CommandRoleExecution.RUNTIME_HANDOFF,
                        "Policy-gated runtime handoff only after planning artifacts are ready.",
                        f"{run_root}/runtime-handoff.md",
                        approval_required=True,
                    ),
                ),
            ),
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt=(
                    "Policy-gated implementation handoff. Use only after PRD, test spec, "
                    "and execution brief are accepted; do not silently launch runtime from preview."
                ),
                brief_file=f"{run_root}/runtime-handoff.md",
                expected_artifacts=(f"{run_root}/runtime-handoff.md",),
            ),
        ),
    )
    return recipe
