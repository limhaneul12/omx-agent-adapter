from __future__ import annotations

from pathlib import Path
import sys

import pytest
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.schemas.invoke_schemas import OmxCommandResult

runner = CliRunner()


def test_ralph_launch_rejects_blank_task() -> None:
    result = runner.invoke(app, ["ralph", "launch", "--task", "   "])

    assert result.exit_code != 0
    assert "Task text must not be blank" in result.stdout


def test_ralph_launch_rejects_non_tty_without_force_detach(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    result = runner.invoke(app, ["ralph", "launch", "--task", "Ship feature"])

    assert result.exit_code != 0
    assert "requires an interactive TTY" in result.stdout


def test_ralph_launch_rejects_existing_state_without_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text("{}")

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
    assert "Existing Ralph state detected" in result.stdout
    assert "cleanup-stale" in result.stdout


def test_ralph_launch_runs_preflight_and_command_when_forced(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text("{}")

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
    (state_dir / "ralph-state.json").write_text('{"status":"active"}')

    observed_commands: list[list[str]] = []

    def fake_run_omx_command(command: list[str], cwd: str | None = None) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr("omx_remote.cli.run_omx_command", fake_run_omx_command)

    result = runner.invoke(app, ["ralph", "resume"])

    assert result.exit_code == 0
    assert observed_commands == [["ralph"]]


def test_ralph_resume_promotes_no_resumable_state_to_preflight_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ralph-state.json").write_text('{"status":"active"}')

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
    stale_state.write_text("{}")
    stale_progress.write_text("{}")
    keep_file.write_text("{}")

    result = runner.invoke(app, ["ralph", "cleanup-stale"])

    assert result.exit_code == 0
    assert not stale_state.exists()
    assert not stale_progress.exists()
    assert keep_file.exists()
    assert "ralph-state.json" in result.stdout
    assert "ralph-progress.json" in result.stdout
