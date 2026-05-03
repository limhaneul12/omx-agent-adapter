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
    assert "Quick start" in completed_process.stdout
    assert "agent-remote version" in completed_process.stdout


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
