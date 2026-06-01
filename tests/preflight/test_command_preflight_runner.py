from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.runtime.preflight.command_preflight_runner import run_command_preflight
from omx_remote.schemas.preflight_schemas import PreflightReportStatus


def test_command_preflight_reports_builtin_read_only_command(tmp_path: Path) -> None:
    report = run_command_preflight("builtin:review-gate", cwd=tmp_path)

    assert report.command_id == "review-gate"
    assert report.status in {
        PreflightReportStatus.PASSED,
        PreflightReportStatus.WARNING,
        PreflightReportStatus.BLOCKED,
    }
    assert any(check.category == "tool_availability" for check in report.checks)


def test_command_preflight_blocks_missing_prompt_file(tmp_path: Path) -> None:
    (tmp_path / ".comx-agent.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/missing.md"
""".strip()
    )

    report = run_command_preflight("repo:codex_review", cwd=tmp_path)

    assert report.status == PreflightReportStatus.BLOCKED
    assert any("Prompt file does not exist" in reason for reason in report.blockers)


def test_preflight_prompt_file_cli_outputs_json(tmp_path: Path) -> None:
    prompt_path = tmp_path / "task.md"
    prompt_path.write_text("Do the task.")

    result = CliRunner().invoke(
        app,
        [
            "preflight",
            "prompt-file",
            str(prompt_path),
            "--cwd",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["checks"][0]["category"] == "prompt_file_visibility"
    assert payload["status"] == "passed"


def test_preflight_run_cli_outputs_json(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["preflight", "run", "builtin:review-gate", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["command_id"] == "review-gate"
    assert "checks" in payload


def test_preflight_route_omx_team_returns_report(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["preflight", "route", "omx-team", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["route"] == "omx-team"
    assert any(check["category"] == "git_state" for check in payload["checks"])
