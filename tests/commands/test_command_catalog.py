from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.commands.builtin_command_catalog import (
    build_builtin_command_catalog,
)
from omx_remote.runtime.commands.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.command_recipe_loader import load_repo_command_recipes
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)

NEW_COMMAND_IDS = {
    "collaboration-kickoff",
    "team-standup-sync",
    "integration-room",
    "conflict-resolution-council",
    "parallel-review-board",
    "release-readiness-room",
    "idea-to-prd-council",
}

EXPECTED_NEW_COMMAND_RISKS = {
    "collaboration-kickoff": CommandRisk.LONG_RUNNING,
    "team-standup-sync": CommandRisk.READ_ONLY,
    "integration-room": CommandRisk.LONG_RUNNING,
    "conflict-resolution-council": CommandRisk.LONG_RUNNING,
    "parallel-review-board": CommandRisk.LONG_RUNNING,
    "release-readiness-room": CommandRisk.WRITES_FILES,
    "idea-to-prd-council": CommandRisk.LONG_RUNNING,
}


def _write_builtin_agent_config(workspace: Path) -> None:
    agent_blocks = [
        f"""
[agents.{agent_id}]
enabled = true
provider = "codex"
role = "{agent_id}"
model = "gpt-5.5"
effort = "high"
persona = "Test {agent_id} persona."
""".strip()
        for agent_id in (
        "architect",
        "critic",
        "planner",
        "researcher",
        "team-executor",
        "test-engineer",
        "verifier",
        "writer",
        )
    ]
    (workspace / ".agent-remote.toml").write_text(
        "\n\n".join(agent_blocks), encoding="utf-8"
    )


def test_builtin_catalog_contains_review_command_and_prunes_weak_legacy_builtins() -> None:
    catalog = build_builtin_command_catalog()

    command_ids = [recipe.id for recipe in catalog.commands]
    assert "review-diff" in command_ids
    assert "verify-handoff" not in command_ids
    assert "mcp-registry-inspect" not in command_ids
    assert "company-build-loop" not in command_ids
    assert catalog.find("builtin:review-diff") is not None


def test_builtin_catalog_contains_custom_workflow_commands() -> None:
    catalog = build_builtin_command_catalog()

    command_ids = {recipe.id for recipe in catalog.commands}

    assert {
        "codex-deep-research",
        "omx-autoresearch-loop",
        "research-interview-prd",
        "verify-handoff-plus",
        "route-doctor",
        "mcp-onboard-audit",
        "subagent-review-wave",
        "upstream-contract-refresh",
        "skillize-workflow",
        "run-ledger-closeout",
        "alexandria-memory-capture",
        "docs-sync-guardian",
        "dependency-incident-audit",
        "migration-checkpoint-loop",
        "company-discovery-loop",
        "company-build-loop-plus",
        "product-council",
        "team-sprint-plan",
        "subagent-research-swarm",
        "ultragoal-story-factory",
        "qa-war-room",
        "librarian-closeout",
    }.issubset(command_ids)
    assert len(catalog.commands) == 31
    assert len({recipe.qualified_id for recipe in catalog.commands}) == len(
        catalog.commands
    )


def test_custom_workflow_builtin_contracts_are_typed() -> None:
    catalog = build_builtin_command_catalog()

    research_recipe = catalog.find("builtin:research-interview-prd")
    assert research_recipe is not None
    assert research_recipe.risk == CommandRisk.LONG_RUNNING
    assert [step.command for step in research_recipe.steps] == [
        CommandStepCommand.CODEX_EXEC,
        CommandStepCommand.CODEX_EXEC,
        CommandStepCommand.PROMPT_ONLY,
        CommandStepCommand.CODEX_EXEC,
        CommandStepCommand.PROMPT_ONLY,
        CommandStepCommand.CODEX_EXEC,
    ]
    assert research_recipe.steps[0].codex_search is True
    assert research_recipe.steps[-1].expected_artifacts == (
        ".agent-remote/runs/research-interview-prd/prd.md",
        ".agent-remote/runs/research-interview-prd/test-spec.md",
        ".agent-remote/runs/research-interview-prd/staffing-plan.md",
    )

    deep_research_recipe = catalog.find("builtin:codex-deep-research")
    assert deep_research_recipe is not None
    assert deep_research_recipe.steps[0].inline_prompt is not None
    assert "<task>" in deep_research_recipe.steps[0].inline_prompt

    swarm_recipe = catalog.find("builtin:subagent-research-swarm")
    assert swarm_recipe is not None
    assert swarm_recipe.steps[0].inline_prompt is not None
    assert "<task>" in swarm_recipe.steps[0].inline_prompt
    assert swarm_recipe.steps[0].expected_artifacts == ()

    company_plus_recipe = catalog.find("builtin:company-build-loop-plus")
    assert company_plus_recipe is not None
    assert company_plus_recipe.risk == CommandRisk.LAUNCHES_RUNTIME
    assert any(
        step.command == CommandStepCommand.OMX_ULTRAGOAL
        for step in company_plus_recipe.steps
    )


def test_dogfood_workflow_builtins_expose_expected_risk_and_artifacts() -> None:
    catalog = build_builtin_command_catalog()

    route_doctor = catalog.find("builtin:route-doctor")
    assert route_doctor is not None
    assert route_doctor.risk == CommandRisk.READ_ONLY
    assert route_doctor.steps[-1].output_last_message == (
        ".agent-remote/runs/route-doctor/report.md"
    )

    story_factory = catalog.find("builtin:ultragoal-story-factory")
    assert story_factory is not None
    assert story_factory.risk == CommandRisk.LAUNCHES_RUNTIME
    assert story_factory.steps[-1].command == CommandStepCommand.OMX_ULTRAGOAL
    assert story_factory.steps[-1].brief_file == (
        ".agent-remote/runs/ultragoal-story-factory/stories.md"
    )

    memory_capture = catalog.find("builtin:alexandria-memory-capture")
    assert memory_capture is not None
    assert memory_capture.risk == CommandRisk.WRITES_FILES
    assert memory_capture.steps[0].expected_artifacts == (
        "/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/<descriptive-title>.md",
    )


def test_builtin_catalog_contains_new_collaboration_and_research_commands() -> None:
    catalog = build_builtin_command_catalog()

    command_ids = {recipe.id for recipe in catalog.commands}

    assert NEW_COMMAND_IDS.issubset(command_ids)
    for command_id in NEW_COMMAND_IDS:
        assert catalog.find(f"builtin:{command_id}") is not None


def test_new_builtin_commands_expose_expected_risks_and_step_shapes() -> None:
    catalog = build_builtin_command_catalog()

    for command_id, expected_risk in EXPECTED_NEW_COMMAND_RISKS.items():
        recipe = catalog.find(f"builtin:{command_id}")
        assert recipe is not None
        assert recipe.risk == expected_risk
        assert recipe.steps

    team_standup = catalog.find("builtin:team-standup-sync")
    assert team_standup is not None
    assert [step.command for step in team_standup.steps[:3]] == [
        CommandStepCommand.LOCAL,
        CommandStepCommand.LOCAL,
        CommandStepCommand.LOCAL,
    ]
    assert all("dispatch" not in " ".join(step.argv) for step in team_standup.steps)

    release_room = catalog.find("builtin:release-readiness-room")
    assert release_room is not None
    release_prompts = "\n".join(step.inline_prompt or "" for step in release_room.steps)
    for required_term in (
        "verification_results",
        "review_board_verdict",
        "docs_verdict",
        "run_ledger_evidence",
        "Alexandria closeout",
        "approve_block_verdict",
    ):
        assert required_term in release_prompts

    idea = catalog.find("builtin:idea-to-prd-council")
    assert idea is not None
    idea_prompts = "\n".join(step.inline_prompt or "" for step in idea.steps)
    assert "Alexandria intake" in idea_prompts
    assert "Alexandria closeout" in idea_prompts
    assert "librarian subagent" in idea_prompts
    assert "Roles: librarian" not in idea_prompts
    assert sum(1 for step in idea.steps if step.codex_search) >= 2
    gap_steps = tuple(
        step
        for step in idea.steps
        if step.output_last_message is not None
        and step.output_last_message.endswith("/02_research/gap_research.md")
    )
    assert len(gap_steps) == 1
    assert gap_steps[0].codex_search is False
    assert "do not run more live web research" in (gap_steps[0].inline_prompt or "")
    validation_steps = tuple(
        step
        for step in idea.steps
        if any(
            artifact.endswith("/05_validation/validation_verdict.md")
            for artifact in step.expected_artifacts
        )
    )
    assert len(validation_steps) == 1
    assert validation_steps[0].command == CommandStepCommand.LOCAL
    assert validation_steps[0].agent is None
    assert validation_steps[0].prompt_file is None
    assert "Approve PRD handoff readiness only" in (
        validation_steps[0].inline_prompt or ""
    )
    closeout_steps = tuple(
        step
        for step in idea.steps
        if any(
            artifact.endswith("/current/07_closeout/closeout.md")
            for artifact in step.expected_artifacts
        )
    )
    assert len(closeout_steps) == 1
    assert closeout_steps[0].command == CommandStepCommand.LOCAL
    assert closeout_steps[0].prompt_file is None
    assert "summary-only Alexandria closeout" in (
        closeout_steps[0].inline_prompt or ""
    )
    assert idea.steps[-1].command == CommandStepCommand.OMX_ULTRAGOAL


def test_new_builtin_commands_declare_expected_artifacts() -> None:
    catalog = build_builtin_command_catalog()

    expected_terms = {
        "collaboration-kickoff": ("collaboration_plan", "team_handoff"),
        "team-standup-sync": ("standup_report", "suggested_dispatches"),
        "integration-room": (
            "conflict_matrix",
            "accepted_output_ledger",
            "verification_plan",
        ),
        "conflict-resolution-council": ("adr_decision",),
        "parallel-review-board": ("review_verdict", "security", "tests"),
        "release-readiness-room": (
            "release_verdict",
            "verification_evidence",
            "run_ledger_evidence",
        ),
        "idea-to-prd-council": (
            "workspaces/idea-to-prd-council/<product_slug>/current/00_intake/idea.md",
            "workspaces/idea-to-prd-council/<product_slug>/current/01_memory/similar_ideas.md",
            "workspaces/idea-to-prd-council/<product_slug>/current/02_research/evidence_ledger.md",
            "workspaces/idea-to-prd-council/<product_slug>/current/04_prd/prd.md",
            "workspaces/idea-to-prd-council/<product_slug>/current/04_prd/test_spec.md",
            "workspaces/idea-to-prd-council/<product_slug>/current/04_prd/execution_plan.md",
            "workspaces/idea-to-prd-council/<product_slug>/current/06_ultragoal/ultragoal_brief.md",
            "validation_verdict.md",
        ),
    }

    for command_id, terms in expected_terms.items():
        recipe = catalog.find(f"builtin:{command_id}")
        assert recipe is not None
        artifact_items: list[str] = []
        for step in recipe.steps:
            if step.output_last_message is not None:
                artifact_items.append(step.output_last_message)
            artifact_items.extend(step.expected_artifacts)
        artifact_text = "\n".join(artifact_items)
        for term in terms:
            assert term in artifact_text

    idea = catalog.find("builtin:idea-to-prd-council")
    assert idea is not None
    idea_artifacts = tuple(
        artifact
        for step in idea.steps
        for artifact in (
            (step.output_last_message,) if step.output_last_message else ()
        )
        + step.expected_artifacts
    )
    assert any(
        "workspaces/idea-to-prd-council/<product_slug>/current/00_intake/idea.md"
        in artifact
        for artifact in idea_artifacts
    )
    assert any(
        "workspaces/idea-to-prd-council/<product_slug>/current/04_prd/prd.md"
        in artifact
        for artifact in idea_artifacts
    )
    assert any(
        "workspaces/idea-to-prd-council/<product_slug>/current/06_ultragoal/ultragoal_brief.md"
        in artifact
        for artifact in idea_artifacts
    )


def test_new_builtin_commands_do_not_write_to_personal_absolute_paths() -> None:
    catalog = build_builtin_command_catalog()

    for command_id in NEW_COMMAND_IDS:
        recipe = catalog.find(f"builtin:{command_id}")
        assert recipe is not None
        artifact_items: list[str] = []
        for step in recipe.steps:
            if step.output_last_message is not None:
                artifact_items.append(step.output_last_message)
            artifact_items.extend(step.expected_artifacts)
            artifact_items.extend(
                role.artifact for role in step.role_lanes if role.artifact is not None
            )

        assert not any(
            artifact.startswith("/Users/imhaneul") for artifact in artifact_items
        )


def test_catalog_rejects_duplicate_ids_inside_one_source() -> None:
    recipe = CommandRecipe(
        id="review-diff",
        source=CommandSource.BUILTIN,
        description="Review the current diff.",
        risk=CommandRisk.READ_ONLY,
        steps=(
            CommandStep(command=CommandStepCommand.CODEX_EXEC, inline_prompt="Review."),
        ),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        type(build_builtin_command_catalog()).model_validate(
            {"commands": (recipe, recipe)}
        )


def test_repo_command_recipe_loader_reads_prompt_file_command(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
agent = "reviewer"
provider = "codex"
mode = "exec"
prompt_file = "prompts/review.md"
output_last_message = ".agent-remote/runs/review/final-message.md"
risk = "read_only"
""".strip()
    )

    recipes = load_repo_command_recipes(cwd=tmp_path)

    assert len(recipes) == 1
    assert recipes[0].id == "codex_review"
    assert recipes[0].source == CommandSource.REPO
    assert recipes[0].steps[0].command == CommandStepCommand.CODEX_EXEC
    assert recipes[0].steps[0].agent == "reviewer"
    assert recipes[0].steps[0].prompt_file == "prompts/review.md"


def test_repo_command_recipe_loader_reads_multistep_command(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.refactor_with_review]
description = "Implement, verify, then review."
risk = "writes_files"
steps = [
  { command = "codex_exec", agent = "implementer", prompt_file = "prompts/implement.md" },
  { command = "local", argv = ["uv", "run", "pytest", "-q"] },
  { command = "codex_exec", agent = "reviewer", inline_prompt = "Review the resulting diff." },
]
""".strip()
    )

    recipes = load_repo_command_recipes(cwd=tmp_path)

    assert recipes[0].steps[0].command == CommandStepCommand.CODEX_EXEC
    assert recipes[0].steps[1].command == CommandStepCommand.LOCAL
    assert recipes[0].steps[1].argv == ("uv", "run", "pytest", "-q")
    assert recipes[0].steps[2].inline_prompt == "Review the resulting diff."


def test_repo_command_recipe_loader_reads_mcp_tool_command(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.read_state]
description = "Read active state through MCP."
provider = "mcp"
mode = "tool"
mcp_server = "local_state"
mcp_tool = "state_list_active"
mcp_arguments = { mode = "state" }
""".strip()
    )

    recipes = load_repo_command_recipes(cwd=tmp_path)

    assert recipes[0].steps[0].command == CommandStepCommand.MCP_TOOL
    assert recipes[0].steps[0].mcp_server == "local_state"
    assert recipes[0].steps[0].mcp_tool == "state_list_active"
    assert recipes[0].steps[0].mcp_arguments == {"mode": "state"}


def test_repo_command_recipe_unknown_key_fails(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.review]
description = "Review."
provider = "codex"
mode = "exec"
inline_prompt = "Review."
unexpected = true
""".strip()
    )

    with pytest.raises(ValidationError, match="unexpected"):
        load_repo_command_recipes(cwd=tmp_path)


def test_catalog_resolver_handles_builtin_repo_and_ambiguous_names(
    tmp_path: Path,
) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.review-diff]
description = "Repo-specific review."
provider = "codex"
mode = "exec"
inline_prompt = "Review with repo-specific rules."
""".strip()
    )

    catalog = load_command_catalog(cwd=tmp_path)

    assert (
        resolve_command_recipe(catalog, "builtin:review-diff").source
        == CommandSource.BUILTIN
    )
    assert (
        resolve_command_recipe(catalog, "repo:review-diff").source == CommandSource.REPO
    )
    with pytest.raises(CommandCatalogResolutionError, match="ambiguous"):
        resolve_command_recipe(catalog, "review-diff")


def test_builtin_workflows_are_addressable_by_agent_autonomy_policy(
    tmp_path: Path,
) -> None:
    from omx_remote.runtime.commands.agent_autonomy_policy import AgentAutonomyPolicy
    from omx_remote.runtime.commands.command_step_planner import (
        build_command_execution_plan,
    )
    from omx_remote.schemas.commands.command_execution_schemas import (
        CommandAutonomyDecisionKind,
    )

    catalog = build_builtin_command_catalog()
    policy = AgentAutonomyPolicy()
    _write_builtin_agent_config(tmp_path)

    blocked: list[str] = []
    for recipe in catalog.commands:
        plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)
        decision = policy.decide(plan)
        if decision.decision == CommandAutonomyDecisionKind.BLOCK:
            blocked.append(recipe.qualified_id)

    assert blocked == []
