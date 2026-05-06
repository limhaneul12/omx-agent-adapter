from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from omx_remote.adapter_types.ralph_types import (
    RalphTeamDagAdminPolicyPayload,
    RalphTeamDagNodePayload,
    RalphTeamDagPayload,
    RalphWorkerAuthorizationPayload,
)
from omx_remote.cli import app
from omx_remote.runtime.ralph.ralph_control import build_ralph_team_launch_plan
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult

runner = CliRunner()


def _write_valid_prd_artifact(
    tmp_path: Path,
    *,
    objective: str = "Ship feature",
    requires_team_fanout: bool = False,
    team_worker_count: int | None = None,
    team_worker_assignments: list[dict[str, object]] | None = None,
    team_admin: dict[str, object] | None = None,
) -> None:
    prd_dir = tmp_path / ".omx"
    prd_dir.mkdir(exist_ok=True)
    prd_path = prd_dir / "prd.json"
    prd_payload = {
        "objective": objective,
        "scope": ["keep the slice narrow"],
        "constraints": ["keep Ralph independently operable"],
        "execution_plan": ["validate the PRD contract before launch"],
        "verification_expectations": ["ralph launch rejects malformed artifacts"],
        "requires_team_fanout": requires_team_fanout,
        "team_worker_count": team_worker_count,
        "continuation_policy": "review_required",
    }
    if team_worker_assignments is not None:
        prd_payload["team_worker_assignments"] = team_worker_assignments
    if requires_team_fanout:
        if team_admin is None:
            prd_payload["team_admin"] = _team_admin()
        else:
            prd_payload["team_admin"] = team_admin
    prd_path.write_text(json.dumps(prd_payload), encoding="utf-8")


def _team_admin() -> dict[str, object]:
    return {
        "admin_id": "team-admin",
        "aggregation_policy": "collect_all_workers_then_review",
        "merge_policy": "review_before_merge",
        "completion_policy": "all_required_tasks_completed",
        "requires_human_for": ["merge conflicts or worker scope expansion"],
        "requires_llm_review_for": ["final aggregation report before Ralph review"],
        "final_report_required": True,
    }


def _team_assignment(
    worker_id: str,
    *,
    lane_name: str = "Implementation lane",
    owned_file: str = "src/omx_remote/runtime/ralph_control.py",
) -> dict[str, object]:
    return {
        "worker_id": worker_id,
        "lane_name": lane_name,
        "objective": f"Own {lane_name}",
        "owned_files": [owned_file],
        "read_only_context_files": ["docs/jobs/schema-type-refactor-hardening/8_ralph-prd-to-team-worker-distribution-prompt.md"],
        "forbidden_files": ["src/omx_remote/runtime/codex_goal_supervisor.py"],
        "tdd_steps": ["Write a failing focused regression", "Make the regression pass"],
        "verification_commands": ["uv run pytest tests/runtime/test_ralph_control.py -q"],
        "handoff_summary_required": "Summarize changed files and verification output.",
        "authorization_policy": "preapproved",
        "authorization_scope": {
            "allowed_commands": ["uv run pytest tests/runtime/test_ralph_control.py -q"],
            "forbidden_commands": ["git push"],
            "requires_human_for": ["modify forbidden_files or files outside owned_files"],
            "requires_llm_review_for": ["local checkpoint commit"],
        },
    }


def test_ralph_team_dag_payload_types_expose_stable_contract_keys() -> None:
    assert RalphWorkerAuthorizationPayload.__required_keys__ == frozenset(
        {
            "policy",
            "allowed_commands",
            "forbidden_commands",
            "requires_human_for",
            "requires_llm_review_for",
        }
    )
    assert RalphTeamDagNodePayload.__required_keys__ == frozenset(
        {
            "id",
            "subject",
            "description",
            "role",
            "lane",
            "filePaths",
            "depends_on",
            "authorization",
            "acceptance",
        }
    )
    assert RalphTeamDagAdminPolicyPayload.__required_keys__ == frozenset(
        {
            "admin_id",
            "aggregation_policy",
            "merge_policy",
            "completion_policy",
            "requires_human_for",
            "requires_llm_review_for",
            "final_report_required",
        }
    )
    assert RalphTeamDagPayload.__required_keys__ == frozenset(
        {
            "schema_version",
            "plan_slug",
            "source_prd",
            "worker_policy",
            "admin_policy",
            "nodes",
        }
    )


def test_ralph_launch_rejects_blank_task() -> None:
    result = runner.invoke(app, ["ralph", "launch", "--task", "   "])

    assert result.exit_code != 0
    assert "Task text must not be blank" in result.stdout


def test_ralph_launch_rejects_non_tty_without_force_detach(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    result = runner.invoke(app, ["ralph", "launch", "--task", "Ship feature"])

    assert result.exit_code != 0
    assert "requires an interactive TTY" in result.stdout


def test_ralph_launch_rejects_missing_prd_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    result = runner.invoke(app, ["ralph", "launch", "--task", "Ship feature", "--allow-non-tty"])

    assert result.exit_code != 0
    assert "Missing required PRD.json" in result.stdout


def test_ralph_launch_rejects_invalid_structured_prd_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    prd_dir = tmp_path / ".omx"
    prd_dir.mkdir()
    (prd_dir / "prd.json").write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["ralph", "launch", "--task", "Ship feature", "--allow-non-tty"])

    assert result.exit_code != 0
    assert "Invalid .omx/prd.json" in result.stdout
    assert "execution_plan" in result.stdout


def test_ralph_launch_rejects_task_text_that_mismatches_prd_objective(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _write_valid_prd_artifact(tmp_path, objective="Ship a different feature")

    result = runner.invoke(
        app,
        ["ralph", "launch", "--task", "Ship feature", "--allow-non-tty"],
    )

    assert result.exit_code != 0
    assert "must match the typed Ralph PRD objective" in result.stdout


def test_ralph_launch_uses_canonical_prd_objective_when_task_matches_after_normalization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _write_valid_prd_artifact(tmp_path, objective="Ship feature")

    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(
        app,
        ["ralph", "launch", "--task", "  ship feature  ", "--allow-non-tty"],
    )

    assert result.exit_code == 0
    assert observed_commands == [["ralph", "--prd", "Ship feature"]]


def test_build_ralph_team_launch_plan_uses_canonical_prd_objective_and_worker_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _write_valid_prd_artifact(
        tmp_path,
        objective="Ship feature",
        requires_team_fanout=True,
        team_worker_count=3,
        team_worker_assignments=[
            _team_assignment("worker-1", owned_file="src/impl.py"),
            _team_assignment("worker-2", lane_name="Test lane", owned_file="tests/test_impl.py"),
            _team_assignment("worker-3", lane_name="Docs lane", owned_file="docs/impl.md"),
        ],
    )

    command, warnings = build_ralph_team_launch_plan(allow_non_tty=True)

    assert command == ["team", "3:executor", "Ship feature"]
    assert "allow-non-tty is enabled" in "\n".join(warnings)


def test_build_ralph_team_launch_plan_writes_approved_team_dag_handoff_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _write_valid_prd_artifact(
        tmp_path,
        objective="Ship feature with \"quoted\" task",
        requires_team_fanout=True,
        team_worker_count=2,
        team_worker_assignments=[
            _team_assignment("worker-1", owned_file="src/impl.py"),
            _team_assignment("worker-2", lane_name="Test lane", owned_file="tests/test_impl.py"),
        ],
    )

    command, _warnings = build_ralph_team_launch_plan(allow_non_tty=True)

    assert command == ["team", "2:executor", "Ship feature with \"quoted\" task"]
    plans_dir = tmp_path / ".omx" / "plans"
    prd_path = next(plans_dir.glob("prd-*-ralph-team.md"))
    test_spec_path = next(plans_dir.glob("test-spec-*-ralph-team.md"))
    dag_path = next(plans_dir.glob("team-dag-*-ralph-team.json"))

    prd_text = prd_path.read_text(encoding="utf-8")
    assert 'Launch via omx team 2:executor "Ship feature with \\"quoted\\" task"' in prd_text
    assert test_spec_path.read_text(encoding="utf-8").startswith("# Ralph Team Test Spec")

    dag_payload = json.loads(dag_path.read_text(encoding="utf-8"))
    assert dag_payload["schema_version"] == 1
    assert dag_payload["source_prd"] == prd_path.name
    assert dag_payload["worker_policy"] == {
        "requested_count": 2,
        "count_source": "plan-suggested",
        "strict_max_count": True,
    }
    assert dag_payload["admin_policy"] == {
        "admin_id": "team-admin",
        "aggregation_policy": "collect_all_workers_then_review",
        "merge_policy": "review_before_merge",
        "completion_policy": "all_required_tasks_completed",
        "requires_human_for": ["merge conflicts or worker scope expansion"],
        "requires_llm_review_for": ["final aggregation report before Ralph review"],
        "final_report_required": True,
    }
    assert [node["id"] for node in dag_payload["nodes"]] == ["worker-1", "worker-2"]
    assert dag_payload["nodes"][0]["filePaths"] == ["src/impl.py"]
    assert dag_payload["nodes"][0]["authorization"] == {
        "policy": "preapproved",
        "allowed_commands": ["uv run pytest tests/runtime/test_ralph_control.py -q"],
        "forbidden_commands": ["git push"],
        "requires_human_for": ["modify forbidden_files or files outside owned_files"],
        "requires_llm_review_for": ["local checkpoint commit"],
    }
    assert "Authorization policy: preapproved" in dag_payload["nodes"][0]["description"]
    assert dag_payload["nodes"][1]["lane"] == "Test lane"


def test_build_ralph_team_launch_plan_requires_worker_assignments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _write_valid_prd_artifact(
        tmp_path,
        objective="Ship feature",
        requires_team_fanout=True,
        team_worker_count=3,
    )

    with pytest.raises(ValueError, match="Team worker assignments"):
        build_ralph_team_launch_plan(allow_non_tty=True)


def test_build_ralph_team_launch_plan_rejects_prd_without_team_fanout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _write_valid_prd_artifact(tmp_path, objective="Ship feature")

    with pytest.raises(ValueError, match="does not request Team fanout"):
        build_ralph_team_launch_plan(allow_non_tty=True)


def test_ralph_launch_rejects_existing_state_without_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"active": true}')

    _write_valid_prd_artifact(tmp_path)

    result = runner.invoke(
        app,
        [
            "ralph",
            "launch",
            "--task",
            "Ship feature",
            "--allow-non-tty",
        ],
    )

    assert result.exit_code != 0
    assert "Existing resumable Ralph state detected" in result.stdout
    assert "cleanup-stale" in result.stdout


def test_ralph_launch_reports_warning_for_terminal_stale_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"active": false, "current_phase": "cancelled"}')
    _write_valid_prd_artifact(tmp_path)

    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(
        app,
        [
            "ralph",
            "launch",
            "--task",
            "Ship feature",
            "--allow-non-tty",
        ],
    )

    assert result.exit_code == 0
    assert observed_commands == [["ralph", "--prd", "Ship feature"]]
    assert "Ralph state exists and is terminal/non-runnable." in result.stdout


def test_ralph_launch_runs_preflight_and_command_when_forced(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"active": false, "current_phase": "cancelled"}')
    _write_valid_prd_artifact(tmp_path)

    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(
        app,
        [
            "ralph",
            "launch",
            "--task",
            "Ship feature",
            "--force-cleanup",
            "--allow-non-tty",
        ],
    )

    assert result.exit_code == 0
    assert observed_commands == [["ralph", "--prd", "Ship feature"]]
    assert "Existing resumable" not in result.stdout


def test_ralph_resume_rejects_missing_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["ralph", "resume"])

    assert result.exit_code != 0
    assert "No Ralph state found" in result.stdout


def test_ralph_resume_runs_command_when_state_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"active":true}')

    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(app, ["ralph", "resume"])

    assert result.exit_code == 0
    assert observed_commands == [["ralph"]]


def test_ralph_resume_rejects_terminal_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"active": false, "current_phase": "cancelled"}')

    result = runner.invoke(app, ["ralph", "resume"])

    assert result.exit_code != 0
    assert "No resumable Ralph session found for ralph" in result.stdout


def test_ralph_launch_warns_when_tmux_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("omx_remote.runtime.ralph.ralph_state.which", lambda _: None)
    (tmp_path / ".omx").mkdir()
    _write_valid_prd_artifact(tmp_path)
    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(
        app,
        ["ralph", "launch", "--task", "Ship feature", "--allow-non-tty"],
    )

    assert result.exit_code == 0
    assert observed_commands == [["ralph", "--prd", "Ship feature"]]
    assert "tmux was not detected" in result.stdout


def test_ralph_resume_promotes_no_resumable_state_to_preflight_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"active": true}')

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        return OmxCommandResult(
            exit_code=0,
            stdout="No resumable team found for ralph\n",
            stderr="",
        )

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(app, ["ralph", "resume"])

    assert result.exit_code == 2
    assert "No resumable Ralph session found" in result.stdout


def test_ralph_cleanup_stale_removes_only_known_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    stale_state = state_dir / "ralph-state.json"
    stale_progress = state_dir / "ralph-progress.json"
    keep_file = state_dir / "other.json"
    stale_state.write_text("{}", encoding="utf-8")
    stale_progress.write_text("{}", encoding="utf-8")
    keep_file.write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["ralph", "cleanup-stale"])

    assert result.exit_code == 0
    assert not stale_state.exists()
    assert not stale_progress.exists()
    assert keep_file.exists()
    assert "ralph-state.json" in result.stdout
    assert "ralph-progress.json" in result.stdout
