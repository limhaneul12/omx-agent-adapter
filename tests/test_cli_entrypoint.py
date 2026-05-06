import os
import subprocess
from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStateSnapshot,
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
)


def _run_agent_remote_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the agent-remote console entrypoint against local source."""
    env = os.environ.copy()
    repo_root = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(
        [repo_root, f"{repo_root}/src", os.environ.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    command = ["uv", "run", "agent-remote", *args]
    return subprocess.run(
        command,
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _write_goal_lifecycle_bundle(tmp_path: Path) -> None:
    artifact_dir = tmp_path / ".agent-remote" / "state" / "goal-lifecycle"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal_id": "goal-cli",
        "mirror_state": {
            "goal_id": "goal-cli",
            "objective_text": "Restore lifecycle from CLI.",
            "source": "codex_goal",
            "execution_shape": "ralph_pipeline",
            "review_policy": "continue_automatically",
            "team_worker_count": 2,
            "working_directory": str(tmp_path),
            "codex_command": ["codex", "--enable", "goals"],
            "session_locator": "agent-remote-goal-goal-cli",
            "process_id": 1234,
            "launched_at": "2026-05-05T12:00:00+00:00",
            "handoff_state": "ralph_started",
            "tracking_state": "active",
        },
        "aggregation_report": {
            "admin_id": "team-admin",
            "aggregation_state": "ready_for_ralph_review",
            "merge_ready": True,
            "final_report_required": True,
            "completed_workers": ["worker-1", "worker-2"],
            "missing_workers": [],
            "blocked_workers": [],
            "incomplete_workers": [],
            "requires_human_review": False,
            "requires_llm_review": True,
            "task_count": 2,
            "event_count": 2,
            "summary": "Team Admin collected all worker results.",
        },
    }
    (artifact_dir / "goal-cli.json").write_bytes(orjson.dumps(payload))


def test_package_entrypoint_runs_help() -> None:
    completed_process = _run_agent_remote_command(["--help"])

    assert completed_process.returncode == 0
    assert "AI-friendly observability and context" in completed_process.stdout
    assert "Agent-facing adapter layer" in completed_process.stdout
    assert "runtime" in completed_process.stdout
    assert "team" in completed_process.stdout
    assert "history" in completed_process.stdout
    assert "adapt" in completed_process.stdout
    assert "goal" in completed_process.stdout
    assert "hypergoal" in completed_process.stdout
    assert "ralph" in completed_process.stdout
    assert "ultrawork" in completed_process.stdout
    assert "version" in completed_process.stdout


def test_package_entrypoint_runs_runtime_help() -> None:
    completed_process = _run_agent_remote_command(["runtime", "--help"])

    assert completed_process.returncode == 0
    assert "status" in completed_process.stdout
    assert "active-modes" in completed_process.stdout
    assert "mode-status" in completed_process.stdout
    assert "mode-state" in completed_process.stdout


def test_team_cli_is_split_into_feature_launcher_modules() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    team_cli_path = repo_root / "src" / "omx_remote" / "cli_launcher" / "team_cli.py"
    team_launcher_dir = (
        repo_root / "src" / "omx_remote" / "cli_launcher" / "team_launcher"
    )
    expected_modules = {
        "team_read_cli.py",
        "team_message_cli.py",
        "team_task_cli.py",
        "team_approval_cli.py",
        "team_mailbox_cli.py",
        "team_shutdown_cli.py",
        "team_cleanup_cli.py",
    }

    assert team_launcher_dir.is_dir()
    assert not (team_launcher_dir / "__init__.py").exists()
    assert expected_modules == {
        module_path.name for module_path in team_launcher_dir.glob("*.py")
    }
    assert len(team_cli_path.read_text().splitlines()) <= 80


def test_package_entrypoint_runs_team_help() -> None:
    completed_process = _run_agent_remote_command(["team", "--help"])

    assert completed_process.returncode == 0
    assert "status" in completed_process.stdout
    assert "await-event" in completed_process.stdout
    assert "tasks" in completed_process.stdout
    assert "events" in completed_process.stdout
    assert "worker-status" in completed_process.stdout
    assert "send-message" in completed_process.stdout
    assert "write-inbox" in completed_process.stdout
    assert "broadcast" in completed_process.stdout
    assert "create-task" in completed_process.stdout
    assert "read-task" in completed_process.stdout
    assert "transition-task-status" in completed_process.stdout
    assert "update-task" in completed_process.stdout
    assert "claim-task" in completed_process.stdout
    assert "release-task-claim" in completed_process.stdout
    assert "read-task-approval" in completed_process.stdout
    assert "write-task-approval" in completed_process.stdout
    assert "mailbox-mark-delivered" in completed_process.stdout
    assert "mailbox-mark-notified" in completed_process.stdout
    assert "write-shutdown-request" in completed_process.stdout
    assert "read-shutdown-ack" in completed_process.stdout
    assert "cleanup" in completed_process.stdout
    assert "orphan-cleanup" in completed_process.stdout


def test_package_entrypoint_runs_history_help() -> None:
    completed_process = _run_agent_remote_command(["history", "--help"])

    assert completed_process.returncode == 0
    assert "session-search" in completed_process.stdout


def test_package_entrypoint_runs_adapt_help() -> None:
    completed_process = _run_agent_remote_command(["adapt", "--help"])

    assert completed_process.returncode == 0
    assert "probe" in completed_process.stdout
    assert "status" in completed_process.stdout
    assert "envelope" in completed_process.stdout


def test_package_entrypoint_runs_goal_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "--help"])

    assert completed_process.returncode == 0
    assert "Goal only" in completed_process.stdout
    assert "Goal → Ralph" in completed_process.stdout
    assert "Goal → Team" not in completed_process.stdout
    assert "Goal → Ultrawork" not in completed_process.stdout
    assert "Hypergoal" in completed_process.stdout
    assert "start" in completed_process.stdout
    assert "status" in completed_process.stdout
    assert "template" in completed_process.stdout
    assert "prepare-ralph" in completed_process.stdout
    assert "restore-lifecycle" in completed_process.stdout
    assert "operating-decision" in completed_process.stdout


def test_package_entrypoint_runs_goal_template_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "template", "--help"])

    assert completed_process.returncode == 0
    assert "Codex /goal prompt scaffold" in completed_process.stdout


def test_package_entrypoint_runs_goal_template() -> None:
    completed_process = _run_agent_remote_command(["goal", "template"])

    assert completed_process.returncode == 0
    assert "# Codex /goal Prompt Template" in completed_process.stdout
    assert "Goal:" in completed_process.stdout
    assert "Context:" in completed_process.stdout
    assert "Constraints:" in completed_process.stdout
    assert "Done When:" in completed_process.stdout
    assert "Route guide:" in completed_process.stdout
    assert "Goal only" in completed_process.stdout
    assert "Goal → Ralph" in completed_process.stdout
    assert "Goal → Ralph → Team" in completed_process.stdout
    assert "Ralph → Team" in completed_process.stdout
    assert "Ultrawork only" in completed_process.stdout
    assert "Hypergoal" in completed_process.stdout
    assert "Goal → Ultrawork" not in completed_process.stdout


def test_package_entrypoint_runs_hypergoal_help() -> None:
    completed_process = _run_agent_remote_command(["hypergoal", "--help"])

    assert completed_process.returncode == 0
    assert "template" in completed_process.stdout


def test_package_entrypoint_runs_hypergoal_template() -> None:
    completed_process = _run_agent_remote_command(["hypergoal", "template"])

    assert completed_process.returncode == 0
    assert "# Hypergoal Deep-Work Scaffold" in completed_process.stdout
    assert "Focus window:" in completed_process.stdout
    assert "Recovery checklist:" in completed_process.stdout
    assert "Goal → Ultrawork" not in completed_process.stdout


def test_package_entrypoint_runs_goal_prepare_ralph_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "prepare-ralph", "--help"])

    assert completed_process.returncode == 0
    assert "--source-path" in completed_process.stdout
    assert "--requested-slice" in completed_process.stdout
    assert "--constraint" in completed_process.stdout
    assert "--verification-expectation" in completed_process.stdout
    assert "--cwd" in completed_process.stdout


def test_package_entrypoint_runs_goal_restore_lifecycle_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "restore-lifecycle", "--help"])

    assert completed_process.returncode == 0
    assert "--goal-id" in completed_process.stdout
    assert "--cwd" in completed_process.stdout


def test_package_entrypoint_runs_goal_restore_lifecycle(tmp_path: Path) -> None:
    _write_goal_lifecycle_bundle(tmp_path)

    completed_process = _run_agent_remote_command([
        "goal",
        "restore-lifecycle",
        "--goal-id",
        "goal-cli",
        "--cwd",
        str(tmp_path),
    ])

    assert completed_process.returncode == 0
    output = orjson.loads(completed_process.stdout)
    assert output["bundle"]["goal_id"] == "goal-cli"
    assert output["next_resume_target"] == "ralph_post_team_review"
    assert output["ready_to_resume"] is True


def test_package_entrypoint_runs_goal_operating_decision_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "operating-decision", "--help"])

    assert completed_process.returncode == 0
    assert "--goal-id" in completed_process.stdout
    assert "--team-name" in completed_process.stdout
    assert "--cwd" in completed_process.stdout


def test_package_entrypoint_runs_goal_operating_decision(tmp_path: Path) -> None:
    _write_goal_lifecycle_bundle(tmp_path)

    completed_process = _run_agent_remote_command([
        "goal",
        "operating-decision",
        "--goal-id",
        "goal-cli",
        "--team-name",
        "team-alpha",
        "--cwd",
        str(tmp_path),
    ])

    assert completed_process.returncode == 0
    output = orjson.loads(completed_process.stdout)
    assert output["goal_id"] == "goal-cli"
    assert output["current_stage"] == "ralph_post_team_review_pending"
    assert output["next_action"] == "run_ralph_post_team_review"
    assert output["available_evidence"] == [
        "goal_lifecycle_artifact",
        "team_admin_aggregation_report",
    ]
    assert output["missing_evidence"] == []
    assert output["safe_to_mutate"] is False


def test_package_entrypoint_runs_goal_start_help() -> None:
    completed_process = _run_agent_remote_command(["goal", "start", "--help"])

    assert completed_process.returncode == 0
    assert "--objective" in completed_process.stdout
    assert "--execution-shape" in completed_process.stdout
    assert "--review-policy" in completed_process.stdout
    assert "--team-worker-count" in completed_process.stdout


def test_package_entrypoint_runs_ralph_help() -> None:
    completed_process = _run_agent_remote_command(["ralph", "--help"])

    assert completed_process.returncode == 0
    assert "snapshot" in completed_process.stdout
    assert "startability" in completed_process.stdout
    assert "launch" in completed_process.stdout
    assert "resume" in completed_process.stdout
    assert "cleanup-stale" in completed_process.stdout


def test_ralph_startability_outputs_json(monkeypatch) -> None:
    async def fake_read_runtime_mode_state(request):
        _ = request
        return RuntimeModeStateSnapshot(
            mode="ralph",
            exists=True,
            state={"active": False, "mode": "ralph"},
        )

    async def fake_read_runtime_mode_status(request):
        _ = request
        return RuntimeModeStatusResult(
            requested_mode="ralph",
            found=True,
            mode_snapshot=RuntimeModeStatusSnapshot(
                name="ralph",
                is_active=False,
                phase="cancelled",
                state_path="/tmp/ralph-state.json",
            ),
        )

    monkeypatch.setattr("omx_remote.cli.read_runtime_mode_state", fake_read_runtime_mode_state)
    monkeypatch.setattr("omx_remote.cli.read_runtime_mode_status", fake_read_runtime_mode_status)

    result = CliRunner().invoke(app, ["ralph", "startability"])

    assert result.exit_code == 0
    output = orjson.loads(result.stdout)
    assert output["mode_state"]["mode"] == "ralph"
    assert output["mode_status"]["requested_mode"] == "ralph"


def test_package_entrypoint_runs_ultrawork_help() -> None:
    completed_process = _run_agent_remote_command(["ultrawork", "--help"])

    assert completed_process.returncode == 0
    assert "launch" in completed_process.stdout
    assert "resume" in completed_process.stdout
    assert "cleanup-stale" in completed_process.stdout


def test_package_entrypoint_runs_version() -> None:
    completed_process = _run_agent_remote_command(["version"])

    assert completed_process.returncode == 0
    assert "agent-remote 0.1.0" in completed_process.stdout
