from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.commands.builtin_command_catalog import build_builtin_command_catalog
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


def test_catalog_rejects_duplicate_ids_inside_one_source() -> None:
    recipe = CommandRecipe(
        id="review-diff",
        source=CommandSource.BUILTIN,
        description="Review the current diff.",
        risk=CommandRisk.READ_ONLY,
        steps=(CommandStep(command=CommandStepCommand.CODEX_EXEC, inline_prompt="Review."),),
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


def test_catalog_resolver_handles_builtin_repo_and_ambiguous_names(tmp_path: Path) -> None:
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

    assert resolve_command_recipe(catalog, "builtin:review-diff").source == CommandSource.BUILTIN
    assert resolve_command_recipe(catalog, "repo:review-diff").source == CommandSource.REPO
    with pytest.raises(CommandCatalogResolutionError, match="ambiguous"):
        resolve_command_recipe(catalog, "review-diff")
