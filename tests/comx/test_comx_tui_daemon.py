import subprocess
from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.runtime.comx import tui_daemon_control
from omx_remote.runtime.comx.tui_daemon_control import (
    build_daemon_start_command,
    read_comx_tui_daemon_status,
    start_comx_tui_daemon,
    stop_comx_tui_daemon,
)


def test_daemon_start_command_preview_uses_tmux_and_session_id(tmp_path: Path) -> None:
    preview = build_daemon_start_command(
        tmp_path,
        "daily",
        executable="/opt/bin/comx-agent",
    )

    assert preview.tmux_session == "comx-agent-daily"
    assert preview.tui_session_id == "daily"
    assert preview.cwd == str(tmp_path.resolve())
    assert preview.command[:7] == (
        "tmux",
        "new-session",
        "-d",
        "-s",
        "comx-agent-daily",
        "-c",
        str(tmp_path.resolve()),
    )
    assert "/opt/bin/comx-agent tui" in preview.command[-1]
    assert "--session-id daily" in preview.command[-1]
    assert preview.attach_command == (
        "tmux",
        "attach-session",
        "-t",
        "comx-agent-daily",
    )


def test_daemon_status_reports_tmux_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(tui_daemon_control, "which", lambda _: None)

    status = read_comx_tui_daemon_status(tmp_path, "daily")

    assert status.state == "unavailable"
    assert status.tmux_available is False
    assert status.running is False
    assert "tmux was not detected" in status.warnings[0]


def test_daemon_start_reports_existing_tmux_session(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(tui_daemon_control, "which", lambda _: "/usr/bin/tmux")
    observed_commands: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        observed_commands.append(tuple(command))
        if tuple(command)[:2] == ("tmux", "has-session"):
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, 0, "123\n", "")

    monkeypatch.setattr(tui_daemon_control.subprocess, "run", fake_run)

    result = start_comx_tui_daemon(tmp_path, "daily")

    assert result.action == "already_running"
    assert result.state == "running"
    assert result.running is True
    assert observed_commands == [("tmux", "has-session", "-t", "comx-agent-daily")]


def test_daemon_start_launches_when_tmux_session_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(tui_daemon_control, "which", lambda _: "/usr/bin/tmux")
    observed_commands: list[tuple[str, ...]] = []
    session_exists = False

    def fake_run(command, **kwargs):
        nonlocal session_exists
        command_tuple = tuple(command)
        observed_commands.append(command_tuple)
        if command_tuple[:2] == ("tmux", "has-session"):
            return subprocess.CompletedProcess(
                command,
                0 if session_exists else 1,
                "",
                "",
            )
        if command_tuple[:2] == ("tmux", "new-session"):
            session_exists = True
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(tui_daemon_control.subprocess, "run", fake_run)

    result = start_comx_tui_daemon(tmp_path, "daily")

    assert result.action == "start"
    assert result.state == "running"
    assert result.running is True
    assert observed_commands[0] == ("tmux", "has-session", "-t", "comx-agent-daily")
    assert observed_commands[1][:2] == ("tmux", "new-session")
    assert observed_commands[2] == ("tmux", "has-session", "-t", "comx-agent-daily")


def test_daemon_stop_is_noop_when_session_is_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(tui_daemon_control, "which", lambda _: "/usr/bin/tmux")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "")

    monkeypatch.setattr(tui_daemon_control.subprocess, "run", fake_run)

    result = stop_comx_tui_daemon(tmp_path, "daily")

    assert result.action == "missing"
    assert result.state == "stopped"
    assert result.exit_code == 0
    assert result.running is False


def test_daemon_start_dry_run_cli_outputs_json(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "daemon",
            "start",
            "--cwd",
            str(tmp_path),
            "--session-id",
            "daily",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["tmux_session"] == "comx-agent-daily"
    assert payload["tui_session_id"] == "daily"
    assert payload["command"][:4] == ["tmux", "new-session", "-d", "-s"]
