from __future__ import annotations

from pathlib import Path

import orjson
from comx_harness.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_help_exposes_only_the_goal_surface() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "capabilities",
        "plan",
        "run",
        "handoff",
        "status",
        "events",
        "cancel",
        "resume",
        "artifacts",
        "ade",
        "agent",
    ):
        assert command in result.stdout
    for legacy_command in (
        "company-run",
        "commands",
        "cockpit",
        "team",
        "ralph",
        "ultragoal",
        "ultrawork",
        "prd",
    ):
        assert legacy_command not in result.stdout


def test_capabilities_and_plan_return_json(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    capabilities = runner.invoke(app, ["capabilities"])
    plan = runner.invoke(
        app,
        [
            "plan",
            "Inspect the repository.",
            "--provider",
            "codex",
            "--cwd",
            str(tmp_path),
        ],
    )

    assert capabilities.exit_code == 0
    assert plan.exit_code == 0
    capability_payload = orjson.loads(capabilities.stdout)
    plan_payload = orjson.loads(plan.stdout)
    assert {item["provider"] for item in capability_payload["providers"]} == {
        "codex",
        "omx",
    }
    assert plan_payload["provider"] == "codex"
    assert plan_payload["request"]["objective"] == "Inspect the repository."


def test_cli_run_and_artifact_read_share_the_same_core(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    run_result = runner.invoke(
        app,
        [
            "run",
            "Produce a result.",
            "--provider",
            "omx",
            "--cwd",
            str(tmp_path),
        ],
    )

    assert run_result.exit_code == 0
    record = orjson.loads(run_result.stdout)
    artifact_result = runner.invoke(
        app,
        ["artifacts", record["run_id"], "--cwd", str(tmp_path)],
    )
    assert artifact_result.exit_code == 0
    artifacts = orjson.loads(artifact_result.stdout)
    assert any(
        item["kind"] == "result" and item["exists"] for item in artifacts["artifacts"]
    )


def test_invalid_mutation_boundary_returns_structured_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "plan",
            "Unsafe plan.",
            "--cwd",
            str(tmp_path),
            "--sandbox",
            "workspace-write",
        ],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stderr)
    assert payload["status"] == "error"
    assert payload["code"] == "validation_error"


def test_ade_help_is_available_without_starting_desktop_ui() -> None:
    result = runner.invoke(app, ["ade", "--help"])

    assert result.exit_code == 0
    assert "--cwd" in result.stdout


def test_resume_and_handoff_expose_retry_tokens() -> None:
    resume_help = runner.invoke(app, ["resume", "--help"])
    handoff_help = runner.invoke(app, ["handoff", "--help"])

    assert resume_help.exit_code == 0
    assert handoff_help.exit_code == 0
    assert "--idempotency-key" in resume_help.stdout
    assert "--idempotency-key" in handoff_help.stdout
