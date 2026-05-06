import os
import subprocess
from pathlib import Path

import orjson


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
    assert "Agent-facing adapter layer" in completed_process.stdout
    assert "runtime" in completed_process.stdout
    assert "team" in completed_process.stdout
    assert "history" in completed_process.stdout
    assert "adapt" in completed_process.stdout
    assert "goal" in completed_process.stdout
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
    assert "start" in completed_process.stdout
    assert "status" in completed_process.stdout
    assert "prepare-ralph" in completed_process.stdout
    assert "restore-lifecycle" in completed_process.stdout


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
