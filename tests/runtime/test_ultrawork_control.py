from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.schemas.invoke_command_schemas import OmxCommandResult

runner = CliRunner()


def test_ultrawork_launch_rejects_blank_task() -> None:
    result = runner.invoke(app, ["ultrawork", "launch", "--task", "   "])

    assert result.exit_code != 0
    assert "Task text must not be blank" in result.stdout


def test_ultrawork_launch_rejects_non_tty_without_allow_non_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    result = runner.invoke(
        app,
        [
            "ultrawork",
            "launch",
            "--task",
            "Run integration check",
        ],
    )

    assert result.exit_code != 0
    assert "requires an interactive TTY" in result.stdout


def test_ultrawork_launch_rejects_existing_state_without_force(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ultrawork-state.json").write_text('{"active": true}')

    result = runner.invoke(
        app,
        [
            "ultrawork",
            "launch",
            "--task",
            "Run integration check",
            "--allow-non-tty",
        ],
    )

    assert result.exit_code != 0
    assert "Existing resumable Ultrawork state detected" in result.stdout
    assert "cleanup-stale" in result.stdout


def test_ultrawork_launch_reports_warning_for_terminal_stale_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ultrawork-state.json").write_text(
        '{"active": false, "current_phase": "cancelled"}'
    )

    observed_commands: list[tuple[str, ...]] = []

    def fake_run_omx_command(
        command: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(
        "omx_remote.cli_launcher.cli_facade_dependencies.run_omx_command",
        fake_run_omx_command,
    )

    result = runner.invoke(
        app,
        [
            "ultrawork",
            "launch",
            "--task",
            "Run integration check",
            "--allow-non-tty",
            "--team-size",
            "2",
            "--team-role",
            "executor",
        ],
    )

    assert result.exit_code == 0
    assert observed_commands == [("team", "2:executor", "Run integration check")]
    assert "Ultrawork state exists and is terminal/non-runnable." in result.stdout


def test_ultrawork_launch_runs_preflight_and_command_when_forced(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ultrawork-state.json").write_text(
        '{"active": false, "current_phase": "cancelled"}'
    )

    observed_commands: list[tuple[str, ...]] = []

    def fake_run_omx_command(
        command: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(
        "omx_remote.cli_launcher.cli_facade_dependencies.run_omx_command",
        fake_run_omx_command,
    )

    result = runner.invoke(
        app,
        [
            "ultrawork",
            "launch",
            "--task",
            "Run integration check",
            "--force-cleanup",
            "--allow-non-tty",
        ],
    )

    assert result.exit_code == 0
    assert observed_commands == [("team", "1:executor", "Run integration check")]
    assert "Existing resumable" not in result.stdout


def test_ultrawork_launch_warns_when_tmux_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        "omx_remote.runtime.ultrawork.ultrawork_control.which", lambda _: None
    )

    observed_commands: list[tuple[str, ...]] = []

    def fake_run_omx_command(
        command: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(
        "omx_remote.cli_launcher.cli_facade_dependencies.run_omx_command",
        fake_run_omx_command,
    )

    result = runner.invoke(
        app,
        [
            "ultrawork",
            "launch",
            "--task",
            "Run integration check",
            "--allow-non-tty",
        ],
    )

    assert result.exit_code == 0
    assert observed_commands == [("team", "1:executor", "Run integration check")]
    assert "tmux was not detected" in result.stdout


def test_ultrawork_resume_rejects_missing_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["ultrawork", "resume", "--team-name", "team-7"])

    assert result.exit_code != 0
    assert "No Ultrawork state found" in result.stdout


def test_ultrawork_resume_runs_command_when_state_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ultrawork-state.json").write_text('{"active":true}')

    observed_commands: list[tuple[str, ...]] = []

    def fake_run_omx_command(
        command: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(
        "omx_remote.cli_launcher.cli_facade_dependencies.run_omx_command",
        fake_run_omx_command,
    )

    result = runner.invoke(app, ["ultrawork", "resume", "--team-name", "team-7"])

    assert result.exit_code == 0
    assert observed_commands == [("team", "resume", "team-7")]


def test_ultrawork_resume_rejects_terminal_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ultrawork-state.json").write_text(
        '{"active": false, "current_phase": "cancelled"}'
    )

    result = runner.invoke(app, ["ultrawork", "resume", "--team-name", "team-7"])

    assert result.exit_code != 0
    assert "No resumable Ultrawork session found." in result.stdout


def test_ultrawork_resume_promotes_no_resumable_state_to_preflight_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "ultrawork-state.json").write_text('{"active":true}')

    def fake_run_omx_command(
        command: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        return OmxCommandResult(
            exit_code=0,
            stdout="No resumable team found for team-7\n",
            stderr="",
        )

    monkeypatch.setattr(
        "omx_remote.cli_launcher.cli_facade_dependencies.run_omx_command",
        fake_run_omx_command,
    )

    result = runner.invoke(app, ["ultrawork", "resume", "--team-name", "team-7"])

    assert result.exit_code == 2
    assert "No resumable Ultrawork team found" in result.stdout


def test_ultrawork_cleanup_stale_removes_only_known_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / ".omx" / "state"
    state_dir.mkdir(parents=True)
    stale_state = state_dir / "ultrawork-state.json"
    stale_progress = state_dir / "ultrawork-progress.json"
    keep_file = state_dir / "other.json"
    stale_state.write_text("{}")
    stale_progress.write_text("{}")
    keep_file.write_text("{}")

    result = runner.invoke(app, ["ultrawork", "cleanup-stale"])

    assert result.exit_code == 0
    assert not stale_state.exists()
    assert not stale_progress.exists()
    assert keep_file.exists()
    assert "ultrawork-state.json" in result.stdout
    assert "ultrawork-progress.json" in result.stdout
