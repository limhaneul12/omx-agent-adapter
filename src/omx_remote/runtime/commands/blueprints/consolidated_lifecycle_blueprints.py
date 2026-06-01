from omx_remote.runtime.commands.blueprints.company_run_blueprint import (
    build_company_run_blueprint,
)
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

PUBLIC_WORKFLOW_COMMAND_IDS: tuple[str, ...] = (
    "route-next",
    "discovery-gate",
    "research-brief",
    "idea-to-prd",
    "implementation-kickoff",
    "team-sync",
    "integration-plan",
    "review-gate",
    "release-readiness",
    "company-run",
)


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


def _team_sync_recipe() -> CommandRecipe:
    """Build the team-sync lifecycle recipe.

    Returns:
        CommandRecipe: Team-sync recipe.
    """
    report_path = ".comx-agent/runs/team-sync/status-report.md"
    recipe = CommandRecipe(
        id="team-sync",
        source=CommandSource.BUILTIN,
        description="Read active or recent Team evidence and summarize workers, blockers, and proof layers.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("comx-agent", "team", "status", "--team", "<task>")),
            local_step(("comx-agent", "team", "tasks", "--team", "<task>")),
            local_step(("comx-agent", "team", "events", "--team", "<task>")),
            codex_step(
                "Summarize team-sync status without mutating mailboxes for: <task>.",
                agent="integration_steward",
                prompt_file=prompt_asset_path("team-sync", "team-sync-plan.md"),
                output_last_message=report_path,
                role_lanes=(
                    role_lane(
                        "integration_steward",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Summarize Team workers, blockers, proof layers, and next dispatches.",
                        report_path,
                    ),
                ),
            ),
        ),
    )
    return recipe


def _integration_plan_recipe() -> CommandRecipe:
    """Build the integration-plan lifecycle recipe.

    Returns:
        CommandRecipe: Integration-plan recipe.
    """
    run_root = ".comx-agent/runs/integration-plan"
    recipe = CommandRecipe(
        id="integration-plan",
        source=CommandSource.BUILTIN,
        description="Integrate worker and subagent outputs into decisions, conflicts, and verification order.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Create integration-plan conflict matrix and verification plan for: <task>.",
                agent="integration_steward",
                prompt_file=prompt_asset_path(
                    "integration-plan", "integration-plan.md"
                ),
                output_last_message=f"{run_root}/integration-plan.md",
                expected_artifacts=(
                    f"{run_root}/conflict-matrix.md",
                    f"{run_root}/accepted-decisions.md",
                    f"{run_root}/verification-plan.md",
                ),
                role_lanes=(
                    role_lane(
                        "integration_steward",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Classify outputs, resolve conflicts, and order integration.",
                        f"{run_root}/integration-plan.md",
                    ),
                ),
            ),
        ),
    )
    return recipe


def _review_gate_recipe() -> CommandRecipe:
    """Build the review-gate lifecycle recipe.

    Returns:
        CommandRecipe: Review-gate recipe.
    """
    run_root = ".comx-agent/runs/review-gate"
    recipe = CommandRecipe(
        id="review-gate",
        source=CommandSource.BUILTIN,
        description="Run specialist review lanes and produce an approve/block review verdict.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            local_step(("git", "diff", "--check")),
            local_step(("git", "diff", "--name-only")),
            codex_step(
                "Run review-gate specialist lanes and synthesize approve/block verdict for: <task>.",
                agent="quality_gatekeeper",
                prompt_file=prompt_asset_path("review-gate", "review-gate.md"),
                output_last_message=f"{run_root}/review-verdict.md",
                expected_artifacts=(
                    f"{run_root}/blocking-findings.md",
                    f"{run_root}/non-blocking-recommendations.md",
                    f"{run_root}/required-fixes.md",
                ),
                role_lanes=(
                    role_lane(
                        "quality_gatekeeper",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Produce approve/block review verdict from concrete evidence.",
                        f"{run_root}/review-verdict.md",
                        approval_required=True,
                    ),
                ),
            ),
        ),
    )
    return recipe


def _release_readiness_recipe() -> CommandRecipe:
    """Build the release-readiness lifecycle recipe.

    Returns:
        CommandRecipe: Release-readiness recipe.
    """
    run_root = ".comx-agent/runs/release-readiness"
    recipe = CommandRecipe(
        id="release-readiness",
        source=CommandSource.BUILTIN,
        description="Verify final release readiness, docs, run ledger, and Alexandria MCP closeout.",
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.LIFECYCLE,
        risk=CommandRisk.WRITES_FILES,
        steps=(
            local_step(("git", "diff", "--check")),
            local_step(("uv", "run", "ruff", "check", ".")),
            local_step(("uv", "run", "pyrefly", "check", "src")),
            local_step(("uv", "run", "pytest")),
            codex_step(
                "Assess release-readiness final closeout for: <task>.",
                agent="quality_gatekeeper",
                prompt_file=prompt_asset_path(
                    "release-readiness",
                    "release-readiness.md",
                ),
                output_last_message=f"{run_root}/release-verdict.md",
                expected_artifacts=(
                    f"{run_root}/verification-evidence.md",
                    f"{run_root}/docs-sync.md",
                    f"{run_root}/run-ledger.md",
                    f"{run_root}/alexandria-mcp-closeout.md",
                ),
                role_lanes=(
                    role_lane(
                        "release_manager",
                        CommandRoleExecution.VALIDATION_GATE,
                        "Approve or block release readiness from verification evidence.",
                        f"{run_root}/release-verdict.md",
                        approval_required=True,
                    ),
                    role_lane(
                        "alexandria_mcp_closeout",
                        CommandRoleExecution.ALEXANDRIA_MEMORY,
                        "Use Alexandria MCP tools for curated memory closeout only.",
                        f"{run_root}/alexandria-mcp-closeout.md",
                    ),
                ),
            ),
        ),
    )
    return recipe


def build_public_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build the 10 public workflow recipes.

    Returns:
        tuple[CommandRecipe, ...]: Public workflow recipes.
    """
    recipes = (
        _route_next_recipe(),
        _discovery_gate_recipe(),
        _research_brief_recipe(),
        _idea_to_prd_recipe(),
        _implementation_kickoff_recipe(),
        _team_sync_recipe(),
        _integration_plan_recipe(),
        _review_gate_recipe(),
        _release_readiness_recipe(),
        build_company_run_blueprint(),
    )
    return recipes
