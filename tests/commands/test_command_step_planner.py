from pathlib import Path

from omx_remote.runtime.commands.command_catalog_resolver import load_command_catalog
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRisk,
    CommandSource,
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
    assert "--output-last-message" in plan.steps[0].native_argv
    assert str(tmp_path / ".agent-remote/runs/review/final-message.md") in plan.steps[0].expected_artifacts


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
