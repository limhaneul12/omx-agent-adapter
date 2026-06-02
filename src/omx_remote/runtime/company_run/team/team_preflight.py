import subprocess
from dataclasses import dataclass
from pathlib import Path

_TEAM_SPLIT_STATUS_COMMAND: tuple[str, ...] = (
    "git",
    "status",
    "--short",
    "--untracked-files=all",
    "--",
    ".",
    ":(exclude).comx-agent",
    ":(exclude).omx",
    ":(exclude).codex",
)


@dataclass(frozen=True)
class TeamSplitWorktreePreflight:
    """Git cleanliness result before native Team worktree fanout."""

    allowed: bool
    detail: str


def team_split_worktree_preflight(cwd: Path) -> TeamSplitWorktreePreflight:
    """Check that the leader worktree is clean before Team splits worktrees.

    Args:
        cwd [Path]: Repository root that native OMX Team will operate on.

    Returns:
        TeamSplitWorktreePreflight: Whether native Team fanout is safe.
    """
    completed_process = subprocess.run(
        _TEAM_SPLIT_STATUS_COMMAND,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed_process.returncode != 0:
        detail = (
            completed_process.stderr
            or completed_process.stdout
            or "git status failed before Team fanout"
        ).strip()
        preflight = TeamSplitWorktreePreflight(allowed=False, detail=detail)
        return preflight
    status_text = completed_process.stdout.strip()
    if status_text:
        preflight = TeamSplitWorktreePreflight(allowed=False, detail=status_text)
        return preflight
    preflight = TeamSplitWorktreePreflight(
        allowed=True,
        detail="leader worktree is clean for Team fanout",
    )
    return preflight
