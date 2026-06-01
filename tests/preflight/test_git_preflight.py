import subprocess
from pathlib import Path

from omx_remote.runtime.preflight.git_preflight import check_git_state
from omx_remote.schemas.commands.command_recipe_schemas import CommandRisk
from omx_remote.schemas.preflight_schemas import PreflightSeverity


def test_clean_git_state_passes(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git", "status", "--short"],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_git_state(tmp_path, CommandRisk.WRITES_FILES)

    assert result.severity == PreflightSeverity.INFO
    assert result.blocks_execution is False


def test_dirty_git_state_warns_for_read_only_commands(
    tmp_path: Path, monkeypatch
) -> None:
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git", "status", "--short"],
            returncode=0,
            stdout=" M README.md\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_git_state(tmp_path, CommandRisk.READ_ONLY)

    assert result.severity == PreflightSeverity.WARNING
    assert result.blocks_execution is False
    assert "dirty" in result.summary


def test_dirty_git_state_blocks_mutating_commands(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git", "status", "--short"],
            returncode=0,
            stdout=" M README.md\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_git_state(tmp_path, CommandRisk.LAUNCHES_RUNTIME)

    assert result.severity == PreflightSeverity.BLOCKER
    assert result.blocks_execution is True


def test_git_state_outside_repo_returns_warning(tmp_path: Path, monkeypatch) -> None:
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git", "status", "--short"],
            returncode=128,
            stdout="",
            stderr="not a git repository",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_git_state(tmp_path, CommandRisk.READ_ONLY)

    assert result.severity == PreflightSeverity.WARNING
    assert result.blocks_execution is False
    assert "not a git repository" in result.detail
