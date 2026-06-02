from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.commands.catalog.builtin_command_catalog import (
    build_builtin_command_catalog,
)
from omx_remote.runtime.commands.catalog.command_catalog_resolver import (
    CommandCatalogResolutionError,
    load_command_catalog,
    resolve_command_recipe,
)
from omx_remote.runtime.commands.catalog.command_recipe_loader import load_repo_command_recipes
from omx_remote.runtime.commands.blueprints.adapter_ops_blueprints import (
    ADAPTER_OPS_COMMAND_IDS,
)
from omx_remote.runtime.commands.blueprints.public_workflow_catalog import (
    PUBLIC_WORKFLOW_COMMAND_IDS,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandNamespace,
    CommandRecipe,
    CommandRecipeCategory,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)

TARGET_PUBLIC_IDS = tuple(PUBLIC_WORKFLOW_COMMAND_IDS)
TARGET_ADAPTER_OPS_IDS = tuple(ADAPTER_OPS_COMMAND_IDS)
EXPECTED_PUBLIC_RISKS = {
    "route-next": CommandRisk.READ_ONLY,
    "discovery-gate": CommandRisk.LONG_RUNNING,
    "research-brief": CommandRisk.EXTERNAL_NETWORK,
    "idea-to-prd": CommandRisk.LONG_RUNNING,
    "implementation-kickoff": CommandRisk.LAUNCHES_RUNTIME,
    "team-sync": CommandRisk.READ_ONLY,
    "integration-plan": CommandRisk.LONG_RUNNING,
    "review-gate": CommandRisk.LONG_RUNNING,
    "release-readiness": CommandRisk.WRITES_FILES,
    "company-run": CommandRisk.LAUNCHES_RUNTIME,
}


def _write_builtin_agent_config(workspace: Path) -> None:
    agent_blocks = [
        f"""
[agents.{agent_id}]
enabled = true
provider = "codex"
role = "{agent_id}"
model = "gpt-5.5"
effort = "xhigh"
persona = "Test {agent_id} persona."
""".strip()
        for agent_id in (
            "route_strategist",
            "research_analyst",
            "implementation_architect",
            "integration_steward",
            "quality_gatekeeper",
        )
    ]
    (workspace / ".comx-agent.toml").write_text(
        "\n\n".join(agent_blocks), encoding="utf-8"
    )


def test_builtin_catalog_contains_exactly_ten_public_workflows() -> None:
    catalog = build_builtin_command_catalog()

    public_recipes = tuple(
        recipe
        for recipe in catalog.commands
        if recipe.namespace == CommandNamespace.WORKFLOW
        and recipe.category
        in {
            CommandRecipeCategory.LIFECYCLE,
            CommandRecipeCategory.MACRO,
        }
    )

    assert tuple(recipe.id for recipe in public_recipes) == TARGET_PUBLIC_IDS
    assert len(public_recipes) == 10
    assert len(catalog.commands) == 15
    assert len({recipe.qualified_id for recipe in catalog.commands}) == len(
        catalog.commands
    )


def test_adapter_ops_namespace_contains_exactly_five_maintenance_commands() -> None:
    catalog = build_builtin_command_catalog()

    adapter_ops = tuple(
        recipe
        for recipe in catalog.commands
        if recipe.namespace == CommandNamespace.ADAPTER_OPS
    )

    assert tuple(recipe.display_id for recipe in adapter_ops) == TARGET_ADAPTER_OPS_IDS
    assert tuple(recipe.public_id for recipe in adapter_ops) == (
        "adapter-ops:mcp-audit",
        "adapter-ops:contract-refresh",
        "adapter-ops:skillize",
        "adapter-ops:run-ledger",
        "adapter-ops:memory-capture",
    )
    assert tuple(recipe.id for recipe in adapter_ops) == (
        "mcp-audit",
        "contract-refresh",
        "skillize",
        "run-ledger",
        "memory-capture",
    )
    assert len(adapter_ops) == 5
    assert all(
        recipe.category == CommandRecipeCategory.MAINTENANCE for recipe in adapter_ops
    )
    assert all(
        recipe.qualified_id.startswith("builtin:adapter-ops:") for recipe in adapter_ops
    )
    assert all(
        recipe.display_qualified_id.startswith("builtin:adapter-ops ")
        for recipe in adapter_ops
    )


def test_unknown_command_id_is_not_resolved_as_alias() -> None:
    catalog = build_builtin_command_catalog()

    with pytest.raises(CommandCatalogResolutionError, match="No command named"):
        resolve_command_recipe(catalog, "builtin:not-a-command")


def test_public_workflow_contracts_expose_expected_risks_and_shapes() -> None:
    catalog = build_builtin_command_catalog()

    for command_id, expected_risk in EXPECTED_PUBLIC_RISKS.items():
        recipe = catalog.find(f"builtin:{command_id}")
        assert recipe is not None
        assert recipe.risk == expected_risk
        assert recipe.namespace == CommandNamespace.WORKFLOW
        assert recipe.steps

    assert (
        catalog.find("builtin:route-next").steps[0].command == CommandStepCommand.LOCAL
    )  # type: ignore[union-attr]
    assert catalog.find("builtin:research-brief").steps[0].codex_search is True  # type: ignore[union-attr]
    assert (
        catalog.find("builtin:implementation-kickoff").steps[-1].command
        == CommandStepCommand.OMX_ULTRAGOAL
    )  # type: ignore[union-attr]
    assert catalog.find("builtin:company-run").category == CommandRecipeCategory.MACRO  # type: ignore[union-attr]
    assert catalog.find("builtin:deep-interview") is None
    discovery_recipe = catalog.find("builtin:discovery-gate")
    assert discovery_recipe is not None
    assert "discovery-decision-packet.json" in "\n".join(
        artifact
        for step in discovery_recipe.steps
        for artifact in step.expected_artifacts
    )


def test_company_run_declares_macro_gates_team_subagents_and_alexandria_mcp() -> None:
    catalog = build_builtin_command_catalog()
    recipe = catalog.find("builtin:company-run")
    assert recipe is not None

    role_text = "\n".join(
        f"{lane.id}:{lane.execution}:{lane.purpose}:{lane.artifact}"
        for step in recipe.steps
        for lane in step.role_lanes
    )
    artifact_text = "\n".join(
        artifact
        for step in recipe.steps
        for artifact in (
            ((step.output_last_message,) if step.output_last_message else ())
            + step.expected_artifacts
        )
    )

    for term in (
        "company_orchestrator",
        "discovery_gate",
        "research_council",
        "executive_council",
        "omx_team",
        "alexandria_mcp",
        "codex_subagent",
        "validation_gate",
        "omx_team",
        "alexandria_memory",
    ):
        assert term in role_text
    for artifact in (
        "memory-recall.md",
        "discovery-decision-packet.json",
        "roi-no-build-gate.json",
        "discovery-decision-report.md",
        "research-vote.md",
        "proceed-vote.md",
        "prd-readiness.md",
        "team-plan.md",
        "review-loop.md",
        "release-closeout.md",
    ):
        assert artifact in artifact_text
    assert recipe.steps[-1].command == CommandStepCommand.OMX_TEAM


def test_builtin_commands_do_not_write_to_personal_absolute_paths() -> None:
    catalog = build_builtin_command_catalog()

    for recipe in catalog.commands:
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


def test_catalog_resolver_accepts_adapter_ops_display_and_machine_ids() -> None:
    catalog = build_builtin_command_catalog()

    for command_id in (
        "adapter-ops mcp-audit",
        "builtin:adapter-ops mcp-audit",
        "adapter-ops:mcp-audit",
        "builtin:adapter-ops:mcp-audit",
    ):
        recipe = resolve_command_recipe(catalog, command_id)
        assert recipe.id == "mcp-audit"
        assert recipe.public_id == "adapter-ops:mcp-audit"
        assert recipe.display_id == "adapter-ops mcp-audit"
        assert recipe.namespace == CommandNamespace.ADAPTER_OPS

    for command_id in (
        "adapter-ops/mcp-audit",
        "builtin:adapter-ops/mcp-audit",
    ):
        with pytest.raises(CommandCatalogResolutionError):
            resolve_command_recipe(catalog, command_id)


def test_catalog_rejects_duplicate_ids_inside_one_source() -> None:
    recipe = CommandRecipe(
        id="route-next",
        source=CommandSource.BUILTIN,
        description="Route the current task.",
        risk=CommandRisk.READ_ONLY,
        steps=(
            CommandStep(command=CommandStepCommand.CODEX_EXEC, inline_prompt="Route."),
        ),
    )

    with pytest.raises(ValidationError, match="duplicate"):
        type(build_builtin_command_catalog()).model_validate(
            {"commands": (recipe, recipe)}
        )


def test_adapter_ops_public_id_cannot_be_shadowed_by_workflow_id() -> None:
    step = CommandStep(command=CommandStepCommand.PROMPT_ONLY, inline_prompt="Run.")
    adapter_ops_recipe = CommandRecipe(
        id="mcp-audit",
        source=CommandSource.BUILTIN,
        namespace=CommandNamespace.ADAPTER_OPS,
        description="Audit MCP.",
        steps=(step,),
    )

    with pytest.raises(ValidationError, match="namespace-reserved"):
        CommandRecipe(
            id="adapter-ops:mcp-audit",
            source=CommandSource.BUILTIN,
            namespace=CommandNamespace.WORKFLOW,
            description="Invalid shadow.",
            steps=(step,),
        )

    shadow_recipe = CommandRecipe.model_construct(
        id="adapter-ops:mcp-audit",
        source=CommandSource.BUILTIN,
        namespace=CommandNamespace.WORKFLOW,
        category=CommandRecipeCategory.CUSTOM,
        description="Invalid shadow.",
        risk=CommandRisk.READ_ONLY,
        steps=(step,),
    )

    with pytest.raises(ValidationError, match="namespace-reserved"):
        type(build_builtin_command_catalog()).model_validate(
            {"commands": (adapter_ops_recipe, shadow_recipe)}
        )


def test_repo_command_recipe_loader_reads_prompt_file_command(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
agent = "reviewer"
provider = "codex"
mode = "exec"
prompt_file = "prompts/review.md"
output_last_message = ".comx-agent/runs/review/final-message.md"
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
    (tmp_path / ".comx-agent.toml").write_text(
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
    (tmp_path / ".comx-agent.toml").write_text(
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
    (tmp_path / ".comx-agent.toml").write_text(
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
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.route-next]
description = "Repo-specific route."
provider = "codex"
mode = "exec"
inline_prompt = "Route with repo-specific rules."
""".strip()
    )

    catalog = load_command_catalog(cwd=tmp_path)

    assert (
        resolve_command_recipe(catalog, "builtin:route-next").source
        == CommandSource.BUILTIN
    )
    assert (
        resolve_command_recipe(catalog, "repo:route-next").source == CommandSource.REPO
    )
    with pytest.raises(CommandCatalogResolutionError, match="ambiguous"):
        resolve_command_recipe(catalog, "route-next")


def test_builtin_workflows_are_addressable_by_agent_autonomy_policy(
    tmp_path: Path,
) -> None:
    from omx_remote.runtime.commands.execution.agent_autonomy_policy import AgentAutonomyPolicy
    from omx_remote.runtime.commands.planning.command_step_planner import (
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
