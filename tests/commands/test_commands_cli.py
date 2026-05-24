from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app


def test_commands_list_shows_builtin_commands(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["commands", "list", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert "builtin:review-diff" in [command["qualified_id"] for command in payload["commands"]]
    assert payload["builtin_count"] >= 2


def test_commands_show_outputs_recipe(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["commands", "show", "builtin:verify-handoff", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["recipe"]["id"] == "verify-handoff"
    assert payload["recipe"]["source"] == "builtin"


def test_run_builtin_command_dry_run_outputs_plan(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", "builtin:review-diff", "--cwd", str(tmp_path), "--dry-run", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == "review-diff"
    assert payload["dry_run"] is True
    assert payload["steps"][0]["command"] == "codex_exec"


def test_run_repo_command_dry_run_reads_prompt_file(tmp_path: Path) -> None:
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
""".strip()
    )

    result = CliRunner().invoke(
        app,
        ["run", "repo:codex_review", "--cwd", str(tmp_path), "--dry-run", "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["source"] == "repo"
    assert payload["steps"][0]["prompt_exists"] is True
    assert payload["steps"][0]["prompt_file"] == str(prompt_path)


def test_run_one_off_prompt_file_dry_run(tmp_path: Path) -> None:
    prompt_path = tmp_path / "task.md"
    prompt_path.write_text("Do the task.")

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--provider",
            "codex",
            "--prompt-file",
            str(prompt_path),
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == "one-off-prompt"
    assert payload["steps"][0]["prompt_exists"] is True


def test_run_without_dry_run_is_not_implemented_yet(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", "builtin:review-diff", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "Only --dry-run planning is supported" in payload["error"]
