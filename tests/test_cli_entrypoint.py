import os
import subprocess
from pathlib import Path


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


def test_package_entrypoint_runs_help() -> None:
    completed_process = _run_agent_remote_command(["--help"])

    assert completed_process.returncode == 0
    assert "Agent-facing adapter layer" in completed_process.stdout
    assert "runtime" in completed_process.stdout
    assert "team" in completed_process.stdout
    assert "history" in completed_process.stdout
    assert "adapt" in completed_process.stdout
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
