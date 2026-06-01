import re
import time
from dataclasses import dataclass
from pathlib import Path

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.shared.omx_enums.teamwork_enums import (
    BLOCKED_TASK_STATE_VALUES,
    BLOCKED_WORKER_STATE_VALUES,
    COMPLETED_TASK_STATE_VALUES,
)
from omx_remote.shared.utils.json_file_store import read_required_json_object

_TEAM_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"team(?: name)?[:=]\s*([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"omx team status\s+([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(
        r"team\s+([A-Za-z0-9_.-]+)\s+(?:created|started|launched)", re.IGNORECASE
    ),
)


@dataclass(frozen=True)
class TeamStateCompletionEvidence:
    """Completion proof read from native OMX Team state after await returns."""

    complete: bool
    task_count: int
    completed_count: int
    blocked_count: int
    incomplete_count: int
    blocked_worker_count: int
    detail: str


def team_name_from_output(output: str) -> str | None:
    """Extract a likely OMX Team name from launch output.

    Args:
        output [str]: Captured launch stdout/stderr.

    Returns:
        str | None: Team name when detected.
    """
    for pattern in _TEAM_NAME_PATTERNS:
        match = pattern.search(output)
        if match is not None:
            team_name = match.group(1)
            return team_name
    missing_name: None = None
    return missing_name


def latest_team_state_name(cwd: Path) -> str | None:
    """Return the newest native OMX Team state directory name.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.

    Returns:
        str | None: Team name from the newest state directory when available.
    """
    team_state_root = cwd / ".omx" / "state" / "team"
    if not team_state_root.is_dir():
        missing_name: None = None
        return missing_name
    team_dirs = tuple(path for path in team_state_root.iterdir() if path.is_dir())
    if not team_dirs:
        missing_name = None
        return missing_name
    latest_team_dir = max(team_dirs, key=lambda path: path.stat().st_mtime)
    team_name = latest_team_dir.name
    return team_name


def team_state_evidence_text(cwd: Path, team_name: str | None) -> str:
    """Read bounded native Team startup/status evidence as text.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.
        team_name [str | None]: Team state directory name.

    Returns:
        str: Bounded state evidence text.
    """
    if team_name is None:
        missing_text = ""
        return missing_text
    team_state_dir = cwd / ".omx" / "state" / "team" / team_name
    evidence_paths = (
        team_state_dir / "phase.json",
        team_state_dir / "startup-timing.json",
        team_state_dir / "events" / "events.ndjson",
        *tuple((team_state_dir / "workers").glob("*/status.json")),
    )
    evidence_parts = [
        evidence_path.read_text(encoding="utf-8")[:20_000]
        for evidence_path in evidence_paths
        if evidence_path.is_file()
    ]
    evidence_text = "\n".join(evidence_parts)
    return evidence_text


def _string_value(payload: JsonObject, key: str) -> str | None:
    """Read one string field from a dynamic native Team payload.

    Args:
        payload [dict[str, object]]: JSON object payload.
        key [str]: Field name.

    Returns:
        str | None: String value when present.
    """
    value = payload.get(key)
    if isinstance(value, str):
        return value
    missing_value: None = None
    return missing_value


def team_state_completion_evidence(
    cwd: Path,
    team_name: str | None,
) -> TeamStateCompletionEvidence:
    """Read native Team task/worker state and decide if execution really finished.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.
        team_name [str | None]: Team state directory name.

    Returns:
        TeamStateCompletionEvidence: Completion counts and decision detail.
    """
    if team_name is None:
        return TeamStateCompletionEvidence(
            complete=False,
            task_count=0,
            completed_count=0,
            blocked_count=0,
            incomplete_count=0,
            blocked_worker_count=0,
            detail="no Team name was available for completion evidence",
        )
    team_state_dir = cwd / ".omx" / "state" / "team" / team_name
    task_paths = tuple(sorted((team_state_dir / "tasks").glob("task-*.json")))
    if not task_paths:
        return TeamStateCompletionEvidence(
            complete=False,
            task_count=0,
            completed_count=0,
            blocked_count=0,
            incomplete_count=0,
            blocked_worker_count=0,
            detail="Team state has no task records",
        )

    task_states = tuple(
        (_string_value(read_required_json_object(task_path), "status") or "unknown")
        .strip()
        .lower()
        for task_path in task_paths
    )
    completed_count = sum(
        1 for task_state in task_states if task_state in COMPLETED_TASK_STATE_VALUES
    )
    blocked_count = sum(
        1 for task_state in task_states if task_state in BLOCKED_TASK_STATE_VALUES
    )
    incomplete_count = len(task_states) - completed_count - blocked_count
    worker_state_paths = tuple(
        sorted((team_state_dir / "workers").glob("*/status.json"))
    )
    worker_states = tuple(
        (_string_value(read_required_json_object(worker_path), "state") or "unknown")
        .strip()
        .lower()
        for worker_path in worker_state_paths
    )
    blocked_worker_count = sum(
        1
        for worker_state in worker_states
        if worker_state in BLOCKED_WORKER_STATE_VALUES
    )
    complete = (
        completed_count == len(task_states)
        and blocked_count == 0
        and blocked_worker_count == 0
    )
    detail = (
        f"Team task completion evidence: {completed_count}/{len(task_states)} "
        f"completed, {blocked_count} blocked, {incomplete_count} incomplete, "
        f"{blocked_worker_count} blocked workers."
    )
    return TeamStateCompletionEvidence(
        complete=complete,
        task_count=len(task_states),
        completed_count=completed_count,
        blocked_count=blocked_count,
        incomplete_count=incomplete_count,
        blocked_worker_count=blocked_worker_count,
        detail=detail,
    )


def wait_for_team_completion_evidence(
    cwd: Path,
    team_name: str | None,
    timeout_seconds: float,
) -> TeamStateCompletionEvidence:
    """Poll native Team state until every task is complete or the budget expires.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.
        team_name [str | None]: Team state directory name.
        timeout_seconds [float]: Polling time budget.

    Returns:
        TeamStateCompletionEvidence: Final completion evidence.
    """
    deadline = time.monotonic() + timeout_seconds
    poll_interval_seconds = min(1.0, max(0.05, timeout_seconds / 20.0))
    evidence = team_state_completion_evidence(cwd=cwd, team_name=team_name)
    while not evidence.complete and time.monotonic() < deadline:
        time.sleep(poll_interval_seconds)
        try:
            evidence = team_state_completion_evidence(cwd=cwd, team_name=team_name)
        except ValueError:
            continue
    return evidence
