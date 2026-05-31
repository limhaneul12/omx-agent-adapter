from omx_remote.runtime.commands.command_blueprint_helpers import (
    codex_step,
    local_step,
    prompt_step,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)


def _company_build_loop_plus_recipe() -> CommandRecipe:
    """Implement company build loop plus recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="company-build-loop-plus",
        source=CommandSource.BUILTIN,
        description=(
            "Run the expanded company build loop from an accepted PRD through UltraGoal, "
            "optional Team, verification, review, UltraQA, and memory closeout."
        ),
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            prompt_step(
                "Confirm accepted PRD/test spec, staffing route, and approval gates before "
                "launching any mutating runtime.",
                expected_artifacts=(
                    ".agent-remote/runs/company-build-loop-plus/staffing-plan.md",
                ),
            ),
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt="Create or resume UltraGoal from the accepted PRD/test spec.",
                brief_file=".agent-remote/runs/company-discovery-loop/prd.md",
            ),
            CommandStep(
                command=CommandStepCommand.OMX_TEAM,
                inline_prompt=(
                    "Optional Team launch only inside an active UltraGoal story when "
                    "parallel durable implementation lanes are genuinely useful."
                ),
            ),
            codex_step(
                "Summarize implementation evidence and decide whether to proceed to "
                "verify-handoff-plus, code-review, UltraQA, and librarian-closeout.",
                output_last_message=".agent-remote/runs/company-build-loop-plus/handoff.md",
                expected_artifacts=(
                    ".omx/ultragoal/goals.json",
                    ".omx/ultragoal/ledger.jsonl",
                    ".agent-remote/runs/company-build-loop-plus/handoff.md",
                ),
            ),
        ),
    )
    return recipe


def _subagent_review_wave_recipe() -> CommandRecipe:
    """Implement subagent review wave recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="subagent-review-wave",
        source=CommandSource.BUILTIN,
        description=(
            "Preview a Codex-native parallel review wave for security, tests, "
            "maintainability, performance, and final synthesis."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Spawn read-only Codex subagents for a review wave: one security lane, "
                "one test-gap lane, one maintainability lane, and one performance lane. "
                "Wait for all lanes, require file references, then synthesize findings "
                "with severity, confidence, and approve/block recommendation.",
                output_last_message=".agent-remote/runs/subagent-review-wave/findings.md",
                expected_artifacts=(
                    ".agent-remote/runs/subagent-review-wave/security.md",
                    ".agent-remote/runs/subagent-review-wave/test-gaps.md",
                    ".agent-remote/runs/subagent-review-wave/maintainability.md",
                    ".agent-remote/runs/subagent-review-wave/performance.md",
                ),
            ),
        ),
    )
    return recipe


def _product_council_recipe() -> CommandRecipe:
    """Implement product council recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="product-council",
        source=CommandSource.BUILTIN,
        description=(
            "Run a PM/researcher/architect/critic council that decides build, no-build, "
            "or research-more before implementation."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Run a product council for: <task>. Use role-separated sections: PM scope, researcher "
                "evidence, architect route, skeptic risks, operator recommendation, and "
                "final build/no-build/research-more verdict.",
                output_last_message=".agent-remote/runs/product-council/decision-memo.md",
            ),
        ),
    )
    return recipe


def _team_sprint_plan_recipe() -> CommandRecipe:
    """Implement team sprint plan recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="team-sprint-plan",
        source=CommandSource.BUILTIN,
        description=(
            "Convert a PRD or active UltraGoal story into OMX Team lanes, owner roles, "
            "deliverables, mailbox protocol, and checkpoint expectations."
        ),
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            codex_step(
                "Plan Team sprint lanes for: <task>. Read the PRD or active UltraGoal story and produce "
                "Team sprint lanes: "
                "lead responsibilities, worker roles, task boundaries, artifacts, mailbox "
                "protocol, merge rules, and checkpoint evidence.",
                output_last_message=".agent-remote/runs/team-sprint-plan/team-plan.md",
            ),
            CommandStep(
                command=CommandStepCommand.OMX_TEAM,
                inline_prompt=(
                    "Preview OMX Team launch only after git/runtime preflight and explicit "
                    "approval. Use the generated team-plan as the worker brief."
                ),
            ),
        ),
    )
    return recipe


def _ultragoal_story_factory_recipe() -> CommandRecipe:
    """Implement ultragoal story factory recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="ultragoal-story-factory",
        source=CommandSource.BUILTIN,
        description=(
            "Convert a PRD/test spec into UltraGoal-ready stories, acceptance criteria, "
            "verification commands, and handoff prompts."
        ),
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            codex_step(
                "Generate UltraGoal-ready stories for: <task>. Read the PRD/test spec and include "
                "dependencies, acceptance criteria, verification commands, Team fanout "
                "candidates, rollback notes, and checkpoint evidence.",
                output_last_message=".agent-remote/runs/ultragoal-story-factory/stories.md",
                expected_artifacts=(
                    ".agent-remote/runs/ultragoal-story-factory/stories.md",
                    ".agent-remote/runs/ultragoal-story-factory/acceptance.md",
                    ".agent-remote/runs/ultragoal-story-factory/verification.md",
                ),
            ),
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt=(
                    "Preview `omx ultragoal create-goals` from the story factory output "
                    "after explicit approval."
                ),
                brief_file=".agent-remote/runs/ultragoal-story-factory/stories.md",
            ),
        ),
    )
    return recipe


def _migration_checkpoint_loop_recipe() -> CommandRecipe:
    """Implement migration checkpoint loop recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="migration-checkpoint-loop",
        source=CommandSource.BUILTIN,
        description=(
            "Split a large refactor or migration into UltraGoal checkpoints with "
            "validation gates, rollback notes, and evidence requirements."
        ),
        risk=CommandRisk.LAUNCHES_RUNTIME,
        steps=(
            codex_step(
                "Analyze this migration objective and repository constraints: <task>. Produce "
                "checkpoint slices, invariants, rollback notes, verification commands, "
                "and parallelism boundaries.",
                output_last_message=".agent-remote/runs/migration-checkpoint-loop/plan.md",
            ),
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt=(
                    "Create or update an UltraGoal from the migration checkpoint plan. "
                    "Each story must have acceptance criteria and verification commands."
                ),
                brief_file=".agent-remote/runs/migration-checkpoint-loop/plan.md",
            ),
        ),
    )
    return recipe


def _qa_war_room_recipe() -> CommandRecipe:
    """Implement qa war room recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="qa-war-room",
        source=CommandSource.BUILTIN,
        description=(
            "Run a multi-role verification war room after implementation and produce "
            "approve/block evidence before completion."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            local_step(("git", "diff", "--check")),
            codex_step(
                "Run a QA war room with reviewer, QA, security, performance, and regression "
                "lanes. Gather evidence, missing tests, commands to run, and an approve/block "
                "verdict before UltraGoal checkpoint or final report.",
                output_last_message=".agent-remote/runs/qa-war-room/verdict.md",
                expected_artifacts=(
                    ".agent-remote/runs/qa-war-room/reviewer.md",
                    ".agent-remote/runs/qa-war-room/qa.md",
                    ".agent-remote/runs/qa-war-room/security.md",
                    ".agent-remote/runs/qa-war-room/performance.md",
                ),
            ),
            prompt_step(
                "If verdict is approve, proceed to code-review/UltraQA and then librarian-closeout."
            ),
        ),
    )
    return recipe


def _librarian_closeout_recipe() -> CommandRecipe:
    """Implement librarian closeout recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="librarian-closeout",
        source=CommandSource.BUILTIN,
        description=(
            "Close the loop by verifying artifacts and saving accepted decisions, PRD "
            "paths, verification evidence, and next commands to Alexandria."
        ),
        risk=CommandRisk.WRITES_FILES,
        steps=(
            local_step(("agent-remote", "runs", "list", "--cwd", ".", "--json")),
            prompt_step(
                "Verify final artifacts and write a summary-only closeout note under "
                "`/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/`. Include "
                "decisions, PRD paths, verification evidence, route rationale, and next "
                "commands. Do not store secrets.",
                expected_artifacts=(
                    "/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/<closeout-title>.md",
                ),
            ),
            prompt_step(
                "After saving the file, run alexandria_reindex_vault when available."
            ),
        ),
    )
    return recipe


def build_company_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build company-style execution and verification workflow recipes.

    Returns:
        See function return annotation."""
    recipes = (
        _company_build_loop_plus_recipe(),
        _subagent_review_wave_recipe(),
        _product_council_recipe(),
        _team_sprint_plan_recipe(),
        _ultragoal_story_factory_recipe(),
        _migration_checkpoint_loop_recipe(),
        _qa_war_room_recipe(),
        _librarian_closeout_recipe(),
    )
    return recipes
