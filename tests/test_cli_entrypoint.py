import subprocess


def test_package_entrypoint_runs_help() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "--help"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "Agent-facing adapter layer" in completed_process.stdout
    assert "runtime" in completed_process.stdout
    assert "team" in completed_process.stdout
    assert "history" in completed_process.stdout
    assert "adapt" in completed_process.stdout
    assert "ralph" in completed_process.stdout
    assert "version" in completed_process.stdout


def test_package_entrypoint_runs_runtime_help() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "runtime", "--help"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "status" in completed_process.stdout
    assert "active-modes" in completed_process.stdout
    assert "mode-status" in completed_process.stdout
    assert "mode-state" in completed_process.stdout


def test_package_entrypoint_runs_team_help() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "team", "--help"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "status" in completed_process.stdout
    assert "await-event" in completed_process.stdout
    assert "tasks" in completed_process.stdout
    assert "events" in completed_process.stdout
    assert "worker-status" in completed_process.stdout


def test_package_entrypoint_runs_history_help() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "history", "--help"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "session-search" in completed_process.stdout


def test_package_entrypoint_runs_adapt_help() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "adapt", "--help"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "probe" in completed_process.stdout
    assert "status" in completed_process.stdout
    assert "envelope" in completed_process.stdout


def test_package_entrypoint_runs_ralph_help() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "ralph", "--help"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "snapshot" in completed_process.stdout
    assert "startability" in completed_process.stdout
    assert "launch" in completed_process.stdout
    assert "resume" in completed_process.stdout
    assert "cleanup-stale" in completed_process.stdout


def test_package_entrypoint_runs_version() -> None:
    completed_process = subprocess.run(
        ["uv", "run", "agent-remote", "version"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "agent-remote 0.1.0" in completed_process.stdout
