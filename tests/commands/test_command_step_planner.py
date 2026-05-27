from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.commands.command_catalog_resolver import load_command_catalog
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)


def test_builtin_review_diff_dry_run_plan_is_inspectable(tmp_path: Path) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:review-diff")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.command_id == "review-diff"
    assert plan.source == CommandSource.BUILTIN
    assert plan.dry_run is True
    assert plan.steps[0].command == CommandStepCommand.CODEX_EXEC
    assert plan.steps[0].native_argv[:3] == ("codex", "exec", "--json")
    assert plan.steps[0].inline_prompt is not None
    assert plan.blocked_reasons == ()


def test_builtin_codex_deep_research_plan_includes_search_and_sandbox(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:codex-deep-research")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.EXTERNAL_NETWORK
    assert plan.steps[0].codex_search is True
    assert plan.steps[0].codex_sandbox == "read-only"
    assert plan.steps[0].native_argv[:6] == (
        "codex",
        "--search",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
    )
    assert "--search" in plan.steps[0].native_argv
    assert "--sandbox" in plan.steps[0].native_argv
    assert "read-only" in plan.steps[0].native_argv
    assert plan.blocked_reasons == ()


def test_builtin_research_interview_prd_plan_declares_artifacts(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:research-interview-prd")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.LONG_RUNNING
    assert len(plan.steps) == 6
    assert plan.steps[0].codex_search is True
    assert plan.steps[2].command == CommandStepCommand.PROMPT_ONLY
    assert str(tmp_path / ".agent-remote/runs/research-interview-prd/prd.md") in (
        plan.steps[-1].expected_artifacts
    )
    assert plan.blocked_reasons == ()


def test_builtin_alexandria_memory_capture_plan_targets_vault(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:alexandria-memory-capture")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.WRITES_FILES
    assert plan.steps[0].command == CommandStepCommand.PROMPT_ONLY
    assert plan.steps[0].expected_artifacts == (
        "/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/<descriptive-title>.md",
    )
    assert plan.blocked_reasons == ()


def test_prompt_file_plan_reports_hash_and_native_argv(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompts" / "review.md"
    prompt_path.parent.mkdir()
    prompt_path.write_text("Review the diff.")
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/review.md"
output_last_message = ".agent-remote/runs/review/final-message.md"
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
        str(tmp_path / ".agent-remote/runs/review/final-message.md")
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
    (tmp_path / ".agent-remote.toml").write_text(
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
    (tmp_path / ".agent-remote.toml").write_text(
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


def test_mcp_tool_plan_renders_comx_agent_call(tmp_path: Path) -> None:
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
    (tmp_path / ".agent-remote.toml").write_text(
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
