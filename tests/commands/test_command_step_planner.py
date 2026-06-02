from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.commands.blueprints.adapter_ops_blueprints import (
    ADAPTER_OPS_COMMAND_IDS,
)
from omx_remote.runtime.commands.blueprints.public_workflow_catalog import (
    PUBLIC_WORKFLOW_COMMAND_IDS,
)
from omx_remote.runtime.commands.catalog.command_catalog_resolver import (
    load_command_catalog,
)
from omx_remote.runtime.commands.planning.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
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
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.shared.omx_enums.agent_enums import AgentEffort

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


def _write_agent_config(workspace: Path) -> None:
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


@pytest.mark.parametrize("command_id", PUBLIC_WORKFLOW_COMMAND_IDS)
def test_public_workflow_dry_run_plan_is_inspectable(
    tmp_path: Path, command_id: str
) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find(f"builtin:{command_id}")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="smoke task"
    )

    assert plan.command_id == command_id
    assert plan.qualified_id == f"builtin:{command_id}"
    assert plan.source == CommandSource.BUILTIN
    assert plan.namespace == CommandNamespace.WORKFLOW
    assert plan.dry_run is True
    assert plan.risk == EXPECTED_PUBLIC_RISKS[command_id]
    assert plan.steps
    assert plan.blocked_reasons == ()


@pytest.mark.parametrize("command_id", ADAPTER_OPS_COMMAND_IDS)
def test_adapter_ops_dry_run_plan_is_inspectable(
    tmp_path: Path, command_id: str
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find(f"builtin:{command_id}")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="maintenance task"
    )

    assert plan.command_id == command_id
    assert plan.namespace == CommandNamespace.ADAPTER_OPS
    assert plan.category == CommandRecipeCategory.MAINTENANCE
    assert plan.dry_run is True
    assert plan.steps
    assert plan.blocked_reasons == ()


def test_route_next_dry_run_substitutes_task_in_local_argv(tmp_path: Path) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:route-next")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="choose safe path"
    )

    local_argv_text = "\n".join(
        " ".join(step.native_argv)
        for step in plan.steps
        if step.command == CommandStepCommand.LOCAL
    )
    assert "comx-agent route recommend" in local_argv_text
    assert "choose safe path" in local_argv_text
    assert "<task>" not in local_argv_text


def test_research_brief_plan_includes_search_sandbox_and_prompt_asset(
    tmp_path: Path,
) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:research-brief")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.EXTERNAL_NETWORK
    assert plan.steps[0].codex_search is True
    assert plan.steps[0].codex_sandbox == "read-only"
    assert "--search" in plan.steps[0].native_argv
    assert plan.steps[0].prompt_exists is True
    assert plan.steps[0].prompt_file is not None
    assert "/prompt/research-brief/research-brief-plan.md" in plan.steps[0].prompt_file


def test_codex_plan_argv_receives_model_reasoning_and_madmax_flags(
    tmp_path: Path,
) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:research-brief")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe,
        cwd=tmp_path,
        dry_run=True,
        runtime_options=CommandRuntimeOptions(
            model="gpt-5.5",
            reasoning_effort=AgentEffort.XHIGH,
            madmax=True,
        ),
    )

    argv = plan.steps[0].native_argv
    assert plan.runtime_options is not None
    assert argv[0] == "codex"
    assert argv[argv.index("--model") + 1] == "gpt-5.5"
    assert "gpt-5.5" in argv
    assert 'model_reasoning_effort="xhigh"' in argv
    assert "--dangerously-bypass-approvals-and-sandbox" in argv
    assert argv.index("--model") < argv.index("exec")
    assert argv.index("--dangerously-bypass-approvals-and-sandbox") < argv.index(
        "exec"
    )


def test_idea_to_prd_plan_declares_planning_artifacts(tmp_path: Path) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:idea-to-prd")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    artifact_text = "\n".join(plan.steps[0].expected_artifacts)
    for term in (
        "prd.md",
        "test-spec.md",
        "execution-brief.md",
        "risks-and-decisions.md",
    ):
        assert term in artifact_text
    assert plan.steps[0].role_lanes[-1].approval_required is True


def test_implementation_kickoff_is_policy_gated_runtime_handoff(
    tmp_path: Path,
) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:implementation-kickoff")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].command == CommandStepCommand.CODEX_EXEC
    assert plan.steps[-1].command == CommandStepCommand.OMX_ULTRAGOAL
    assert plan.steps[-1].native_argv[:3] == ("omx", "ultragoal", "create-goals")
    assert "runtime-handoff.md" in "\n".join(plan.steps[0].expected_artifacts)
    assert any(lane.approval_required for lane in plan.steps[0].role_lanes)


def test_team_sync_dry_run_uses_only_read_only_team_inspection(
    tmp_path: Path,
) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:team-sync")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="alpha"
    )

    local_argv_text = "\n".join(
        " ".join(step.native_argv)
        for step in plan.steps
        if step.command == CommandStepCommand.LOCAL
    )
    assert "comx-agent team status --team alpha" in local_argv_text
    assert "comx-agent team tasks --team alpha" in local_argv_text
    assert "comx-agent team events --team alpha" in local_argv_text
    forbidden_terms = (" send ", " dispatch ", " claim ", " complete ", " launch ")
    assert not any(term in f" {local_argv_text} " for term in forbidden_terms)


def test_company_run_phase_order_and_macro_terms_are_visible(tmp_path: Path) -> None:
    _write_agent_config(tmp_path)
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:company-run")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="company idea"
    )

    plan_text = "\n".join(
        "\n".join(
            (
                step.inline_prompt or "",
                " ".join(step.native_argv),
                *step.expected_artifacts,
                *(f"{lane.id}:{lane.purpose}" for lane in step.role_lanes),
            )
        )
        for step in plan.steps
    )
    for term in (
        "company-run",
        "research-vote.md",
        "proceed-vote.md",
        "prd-readiness.md",
        "team-plan.md",
        "review-loop.md",
        "release-closeout.md",
        "research_council",
        "executive_council",
        "alexandria_mcp",
        "Team and subagents",
        "implementation-kickoff",
    ):
        assert term in plan_text
    assert plan.steps[-1].command == CommandStepCommand.OMX_TEAM
    assert plan.steps[-1].native_argv == ("omx", "team", "--help")


def test_adapter_ops_memory_capture_uses_alexandria_mcp_tool_handoff(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:adapter-ops memory-capture")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.WRITES_FILES
    assert plan.steps[0].command == CommandStepCommand.MCP_TOOL
    assert plan.steps[0].mcp_server == "alexandria"
    assert plan.steps[0].mcp_tool == "alexandria_save_note"
    assert plan.steps[0].prompt_exists is True
    assert "Alexandria MCP tools" in (plan.steps[0].inline_prompt or "")


def test_prompt_file_plan_reports_hash_and_native_argv(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompts" / "review.md"
    prompt_path.parent.mkdir()
    prompt_path.write_text("Review the diff.")
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/review.md"
output_last_message = ".comx-agent/runs/review/final-message.md"
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].prompt_file == str(prompt_path)
    assert plan.steps[0].prompt_exists is True
    assert plan.steps[0].prompt_sha256 is not None
    assert plan.steps[0].codex_sandbox == "read-only"
    assert "--sandbox" in plan.steps[0].native_argv
    assert "--output-last-message" in plan.steps[0].native_argv
    assert (
        str(tmp_path / ".comx-agent/runs/review/final-message.md")
        in plan.steps[0].expected_artifacts
    )


def test_codex_step_without_sandbox_defaults_to_read_only(tmp_path: Path) -> None:
    recipe = CommandRecipe(
        id="default-sandbox",
        source=CommandSource.REPO,
        description="Default Codex sandbox.",
        steps=(
            CommandStep(
                command=CommandStepCommand.CODEX_EXEC,
                inline_prompt="Review safely.",
            ),
        ),
    )

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].codex_sandbox == "read-only"
    assert plan.steps[0].native_argv[:5] == (
        "codex",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
    )


def test_missing_prompt_file_blocks_plan(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/missing.md"
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].prompt_exists is False
    assert "Prompt file does not exist" in plan.steps[0].blocked_reasons[0]
    assert plan.blocked_reasons == plan.steps[0].blocked_reasons


def test_missing_agent_reference_blocks_plan(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
agent = "reviewer"
provider = "codex"
mode = "exec"
inline_prompt = "Review."
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert "No agent named reviewer" in plan.steps[0].blocked_reasons[0]


def test_configured_agent_reference_adds_codex_agent_type_override(
    tmp_path: Path,
) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[agents.reviewer]
enabled = true
provider = "codex"
role = "code-reviewer"
model = "gpt-5.5"
effort = "high"
persona = "Review the current diff."

[commands.codex_review]
description = "Review current diff."
agent = "reviewer"
provider = "codex"
mode = "exec"
inline_prompt = "Review."
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.blocked_reasons == ()
    assert plan.steps[0].agent == "reviewer"
    assert plan.steps[0].native_argv[:3] == (
        "codex",
        "-c",
        'agent_type="reviewer"',
    )


def test_mcp_tool_plan_renders_comx_agent_call(tmp_path: Path) -> None:
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
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:read_state")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].command == CommandStepCommand.MCP_TOOL
    assert plan.steps[0].native_argv == (
        "comx-agent",
        "mcp",
        "call",
        "local_state",
        "state_list_active",
    )
    assert plan.steps[0].mcp_arguments == {"mode": "state"}
    assert plan.blocked_reasons == ()


def test_repo_codex_step_supports_search_and_sandbox(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.research]
description = "Research current docs."
provider = "codex"
mode = "exec"
codex_search = true
codex_sandbox = "read-only"
inline_prompt = "Research with citations."
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:research")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].native_argv[:6] == (
        "codex",
        "--search",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
    )


def test_invalid_codex_sandbox_mode_is_rejected() -> None:
    with pytest.raises(ValidationError, match="codex_sandbox"):
        CommandStep(
            command=CommandStepCommand.CODEX_EXEC,
            codex_sandbox="invalid-mode",
        )


def test_codex_options_on_non_codex_step_are_rejected() -> None:
    with pytest.raises(ValidationError, match="command=codex_exec"):
        CommandStep(
            command=CommandStepCommand.LOCAL,
            argv=("echo", "hi"),
            codex_search=True,
        )


def test_incomplete_mcp_tool_plan_reports_blockers(tmp_path: Path) -> None:
    recipe = CommandRecipe(
        id="bad-mcp",
        source=CommandSource.REPO,
        description="Bad MCP recipe.",
        steps=(CommandStep(command=CommandStepCommand.MCP_TOOL),),
    )

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert "MCP tool step requires mcp_server." in plan.blocked_reasons
    assert "MCP tool step requires mcp_tool." in plan.blocked_reasons


def test_one_off_prompt_recipe_uses_prompt_file(tmp_path: Path) -> None:
    prompt_path = tmp_path / "task.md"
    prompt_path.write_text("Do the task.")

    recipe = build_one_off_prompt_recipe(
        provider="codex",
        prompt_file=prompt_path,
        inline_prompt=None,
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.command_id == "one-off-prompt"
    assert plan.risk == CommandRisk.READ_ONLY
    assert plan.steps[0].prompt_file == str(prompt_path)
    assert plan.steps[0].prompt_exists is True
