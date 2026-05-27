import sys
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
    qualified_ids = {command["qualified_id"] for command in payload["commands"]}
    assert "builtin:review-diff" in qualified_ids
    assert "builtin:research-interview-prd" in qualified_ids
    assert payload["builtin_count"] >= 7


def test_commands_show_outputs_recipe(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "commands",
            "show",
            "builtin:verify-handoff",
            "--cwd",
            str(tmp_path),
            "--json",
        ],
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


def test_run_builtin_research_command_renders_codex_search_plan(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "run",
            "builtin:codex-deep-research",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == "codex-deep-research"
    assert payload["risk"] == "external_network"
    assert payload["steps"][0]["codex_search"] is True
    assert "--search" in payload["steps"][0]["native_argv"]
    assert "--sandbox" in payload["steps"][0]["native_argv"]


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


def test_run_requires_dry_run_or_execute(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["run", "builtin:review-diff", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "Pass --dry-run" in payload["error"]


def test_run_repo_local_command_execute_outputs_actual_result(tmp_path: Path) -> None:
    command = f"""
[commands.local_echo]
description = "Run local echo."
risk = "read_only"
steps = [
  {{ command = "local", argv = ["{sys.executable}", "-c", "print('hello')"] }},
]
""".strip()
    (tmp_path / ".agent-remote.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "repo:local_echo",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["steps"][0]["attempts"][0]["exit_code"] == 0
    assert (
        tmp_path / ".agent-remote" / "runs" / payload["run_id"] / "run.json"
    ).exists()


def test_run_execute_failed_actual_result_returns_nonzero(tmp_path: Path) -> None:
    command = f"""
[commands.local_fail]
description = "Run local failure."
risk = "read_only"
steps = [
  {{ command = "local", argv = ["{sys.executable}", "-c", "raise SystemExit(5)"] }},
]
""".strip()
    (tmp_path / ".agent-remote.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "repo:local_fail",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--max-attempts",
            "1",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = orjson.loads(result.stdout)
    assert payload["status"] == "failed"


def test_run_execute_requires_action_returns_soft_stop_code(tmp_path: Path) -> None:
    command = """
[commands.prompt_wait]
description = "Wait for handoff."
risk = "read_only"
steps = [
  { command = "prompt_only", inline_prompt = "Wait for agent action.", expected_artifacts = ["notes/handoff.md"] },
]
""".strip()
    (tmp_path / ".agent-remote.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "repo:prompt_wait",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--json",
        ],
    )

    assert result.exit_code == 3
    payload = orjson.loads(result.stdout)
    assert payload["status"] == "requires_agent_action"


def test_run_execute_requires_explicit_autonomy(tmp_path: Path) -> None:
    command = f"""
[commands.local_echo]
description = "Run local echo."
risk = "read_only"
steps = [
  {{ command = "local", argv = ["{sys.executable}", "-c", "print(\'hello\')"] }},
]
""".strip()
    (tmp_path / ".agent-remote.toml").write_text(command)

    result = CliRunner().invoke(
        app,
        ["run", "repo:local_echo", "--cwd", str(tmp_path), "--execute", "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert "--autonomy agent" in payload["error"]
