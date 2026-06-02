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
)
from omx_remote.schemas.commands.command_role_schemas import CommandRoleExecution


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
