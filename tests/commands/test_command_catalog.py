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


def test_builtin_catalog_contains_review_and_verify_commands() -> None:
    catalog = build_builtin_command_catalog()

    command_ids = [recipe.id for recipe in catalog.commands]
    assert "review-diff" in command_ids
    assert "verify-handoff" in command_ids
    assert catalog.find("builtin:review-diff") is not None


def test_builtin_catalog_contains_custom_workflow_commands() -> None:
    catalog = build_builtin_command_catalog()

    command_ids = {recipe.id for recipe in catalog.commands}

    assert {
        "codex-deep-research",
        "omx-autoresearch-loop",
        "research-interview-prd",
        "company-build-loop",
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
    assert len(catalog.commands) == 27
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

    company_recipe = catalog.find("builtin:company-build-loop")
    assert company_recipe is not None
    assert company_recipe.risk == CommandRisk.LAUNCHES_RUNTIME
    assert company_recipe.steps[1].command == CommandStepCommand.OMX_ULTRAGOAL
    assert company_recipe.steps[2].command == CommandStepCommand.OMX_TEAM


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

    blocked: list[str] = []
    for recipe in catalog.commands:
        plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)
        decision = policy.decide(plan)
        if decision.decision == CommandAutonomyDecisionKind.BLOCK:
            blocked.append(recipe.qualified_id)

    assert blocked == []
