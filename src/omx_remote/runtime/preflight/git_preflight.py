import subprocess
from pathlib import Path

from omx_remote.schemas.commands.command_recipe_schemas import CommandRisk
from omx_remote.schemas.preflight_schemas import (
    PreflightCategory,
    PreflightCheckResult,
    PreflightSeverity,
)


def _dirty_state_blocks(risk: CommandRisk) -> bool:
    """Return whether dirty git state blocks the given command risk.

    Args:
        risk [CommandRisk]: Command or route risk.

    Returns:
        bool: Whether dirty state blocks execution.
    """
    blocks: bool = risk in {
        CommandRisk.WRITES_FILES,
        CommandRisk.LAUNCHES_RUNTIME,
        CommandRisk.LONG_RUNNING,
    }
    return blocks


def check_git_state(cwd: str | Path, risk: CommandRisk) -> PreflightCheckResult:
    """Check git worktree cleanliness for a command or route.

    Args:
        cwd [str | Path]: Working directory to inspect.
        risk [CommandRisk]: Command or route risk.

    Returns:
        PreflightCheckResult: Git preflight result.
    """
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", "status", "--short"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed_process.returncode != 0:
        warning_result = PreflightCheckResult(
            category=PreflightCategory.GIT_STATE,
            severity=PreflightSeverity.WARNING,
            summary="git state could not be read",
            detail=completed_process.stderr
            or completed_process.stdout
            or "git status failed",
            blocks_execution=False,
        )
        return warning_result

    status_text: str = completed_process.stdout.strip()
    if not status_text:
        clean_result = PreflightCheckResult(
            category=PreflightCategory.GIT_STATE,
            severity=PreflightSeverity.INFO,
            summary="git state is clean",
            detail="git status --short returned no changes.",
            blocks_execution=False,
        )
        return clean_result

    blocks_execution: bool = _dirty_state_blocks(risk)
    severity: PreflightSeverity = (
        PreflightSeverity.BLOCKER if blocks_execution else PreflightSeverity.WARNING
    )
    dirty_result = PreflightCheckResult(
        category=PreflightCategory.GIT_STATE,
        severity=severity,
        summary="git state is dirty",
        detail=status_text,
        blocks_execution=blocks_execution,
    )
    return dirty_result
