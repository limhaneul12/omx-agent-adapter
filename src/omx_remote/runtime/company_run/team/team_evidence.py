import re
import time
from dataclasses import dataclass
from pathlib import Path

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.company_run_schemas import (
    CompanyRunNativeTeamListTasksRequest,
    CompanyRunNativeTeamStatusSnapshot,
    CompanyRunNativeTeamTaskListResponse,
)
from omx_remote.shared.omx_enums.teamwork_enums import (
    BLOCKED_TASK_STATE_VALUES,
    BLOCKED_WORKER_STATE_VALUES,
    COMPLETED_TASK_STATE_VALUES,
)
from omx_remote.shared.utils.json_file_store import read_required_json_object
from omx_remote.shared.utils.json_model_dump import model_json_object

_TEAM_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"active team exists\s*\(\s*([A-Za-z0-9_.-]+)\s*\)",
        re.IGNORECASE,
    ),
    re.compile(r'"team_name"\s*:\s*"([A-Za-z0-9_.-]+)"', re.IGNORECASE),
    re.compile(r"team(?: name)?[:=]\s*([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"omx team status\s+([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(
        r"team\s+([A-Za-z0-9_.-]+)\s+(?:created|started|launched)", re.IGNORECASE
    ),
)
_MISSING_TEAM_NAME_SENTINELS: frozenset[str] = frozenset({"missing-team"})


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
    terminal: bool = False


@dataclass(frozen=True)
class TeamTaskOwnerDistributionEvidence:
    """Task-owner distribution proof from native OMX Team task records."""

    valid: bool
    task_count: int
    owner_count: int
    distinct_owner_count: int
    required_distinct_owner_count: int
    missing_owner_count: int
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


def team_name_from_launch_evidence(cwd: Path, output: str) -> str | None:
    """Resolve the actionable Team name from launch output plus local state.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.
        output [str]: Combined launch stdout/stderr evidence.

    Returns:
        str | None: Concrete Team name when available.
    """
    output_team_name = team_name_from_output(output)
    state_team_name = latest_team_state_name(cwd=cwd)
    if _usable_team_name(output_team_name):
        resolved_name = output_team_name
        return resolved_name
    if state_team_name is not None:
        resolved_name = state_team_name
        return resolved_name
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
    team_dirs = tuple(
        path
        for path in team_state_root.iterdir()
        if path.is_dir() and _usable_team_name(path.name)
    )
    if not team_dirs:
        missing_name = None
        return missing_name
    latest_team_dir = max(team_dirs, key=lambda path: path.stat().st_mtime)
    team_name = latest_team_dir.name
    return team_name


def _usable_team_name(team_name: str | None) -> bool:
    """Return whether a candidate Team name is an actionable native Team id.

    Args:
        team_name [str | None]: Candidate Team name.

    Returns:
        bool: True for concrete names, false for known missing placeholders.
    """
    usable = team_name is not None and team_name not in _MISSING_TEAM_NAME_SENTINELS
    return usable


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
            terminal=True,
        )
    command_evidence = _team_status_command_completion_evidence(
        cwd=cwd,
        team_name=team_name,
    )
    if command_evidence is not None:
        return command_evidence
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

    task_payloads = tuple(read_required_json_object(task_path) for task_path in task_paths)
    task_states = tuple(
        (_string_value(task_payload, "status") or "unknown").strip().lower()
        for task_payload in task_payloads
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
    owner_distribution = _task_payload_owner_distribution_evidence(
        task_payloads=task_payloads,
        expected_worker_count=len(worker_state_paths) or None,
    )
    if owner_distribution is not None and not owner_distribution.valid:
        complete = False
    detail = (
        f"Team task completion evidence: {completed_count}/{len(task_states)} "
        f"completed, {blocked_count} blocked, {incomplete_count} incomplete, "
        f"{blocked_worker_count} blocked workers."
    )
    if owner_distribution is not None:
        detail = f"{detail} {owner_distribution.detail}"
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
    while not evidence.complete and not evidence.terminal and time.monotonic() < deadline:
        time.sleep(poll_interval_seconds)
        try:
            evidence = team_state_completion_evidence(cwd=cwd, team_name=team_name)
        except ValueError:
            continue
    return evidence


def _team_status_command_completion_evidence(
    cwd: Path,
    team_name: str,
) -> TeamStateCompletionEvidence | None:
    """Read completion evidence from `omx team status --json`.

    Args:
        cwd [Path]: Repository root where the Team command should run.
        team_name [str]: Native OMX Team name.

    Returns:
        TeamStateCompletionEvidence | None: Completion evidence when the status
        command returned a typed payload; otherwise None so callers may fall back
        to legacy file inspection.
    """
    command_result = run_omx_command(
        arguments=("team", "status", team_name, "--json"),
        cwd=str(cwd),
    )
    stdout = command_result.stdout.strip()
    if command_result.exit_code != 0 or not stdout:
        missing_evidence: None = None
        return missing_evidence
    try:
        status_snapshot = CompanyRunNativeTeamStatusSnapshot.model_validate_json(
            stdout
        )
    except ValueError:
        missing_evidence = None
        return missing_evidence
    if status_snapshot.status == "missing":
        team_state_dir = cwd / ".omx" / "state" / "team" / team_name
        if team_state_dir.is_dir():
            missing_evidence: None = None
            return missing_evidence
        return TeamStateCompletionEvidence(
            complete=False,
            task_count=0,
            completed_count=0,
            blocked_count=0,
            incomplete_count=0,
            blocked_worker_count=0,
            detail=f"omx team status reports Team {team_name} is missing.",
            terminal=True,
        )
    if status_snapshot.tasks is None:
        missing_evidence = None
        return missing_evidence
    task_counts = status_snapshot.tasks
    worker_counts = status_snapshot.workers
    owner_distribution = _team_api_task_owner_distribution_evidence(
        cwd=cwd,
        team_name=team_name,
        expected_worker_count=None if worker_counts is None else worker_counts.total,
    )
    blocked_count = task_counts.blocked + task_counts.failed
    incomplete_count = max(
        0,
        task_counts.total - task_counts.completed - blocked_count,
    )
    blocked_worker_count = (
        0
        if worker_counts is None
        else worker_counts.dead + worker_counts.non_reporting
    )
    complete = (
        task_counts.total > 0
        and task_counts.completed == task_counts.total
        and blocked_count == 0
        and incomplete_count == 0
        and blocked_worker_count == 0
    )
    if owner_distribution is not None and not owner_distribution.valid:
        complete = False
    detail = (
        "Team status command evidence: "
        f"phase={status_snapshot.phase}, status={status_snapshot.status}, "
        f"{task_counts.completed}/{task_counts.total} completed, "
        f"{task_counts.blocked} blocked, {task_counts.failed} failed, "
        f"{task_counts.pending} pending, {task_counts.in_progress} in progress, "
        f"{blocked_worker_count} blocked/non-reporting workers."
    )
    if owner_distribution is not None:
        detail = f"{detail} {owner_distribution.detail}"
    return TeamStateCompletionEvidence(
        complete=complete,
        task_count=task_counts.total,
        completed_count=task_counts.completed,
        blocked_count=blocked_count,
        incomplete_count=incomplete_count,
        blocked_worker_count=blocked_worker_count,
        detail=detail,
    )


def _team_api_task_owner_distribution_evidence(
    cwd: Path,
    team_name: str,
    expected_worker_count: int | None,
) -> TeamTaskOwnerDistributionEvidence | None:
    """Read task-owner distribution through `omx team api list-tasks`.

    Args:
        cwd [Path]: Repository root where the Team command should run.
        team_name [str]: Native OMX Team name.
        expected_worker_count [int | None]: Expected native worker count.

    Returns:
        TeamTaskOwnerDistributionEvidence | None: Owner distribution proof when
        the native API response is available and parseable.
    """
    request = CompanyRunNativeTeamListTasksRequest(team_name=team_name)
    command_result = run_omx_command(
        arguments=(
            "team",
            "api",
            "list-tasks",
            "--input",
            request.model_dump_json(),
            "--json",
        ),
        cwd=str(cwd),
    )
    stdout = command_result.stdout.strip()
    if command_result.exit_code != 0 or not stdout:
        missing_evidence: None = None
        return missing_evidence
    try:
        response = CompanyRunNativeTeamTaskListResponse.model_validate_json(stdout)
    except ValueError:
        missing_evidence = None
        return missing_evidence
    if not response.ok:
        missing_evidence = None
        return missing_evidence
    task_payloads = tuple(model_json_object(task) for task in response.data.tasks)
    evidence = _task_payload_owner_distribution_evidence(
        task_payloads=task_payloads,
        expected_worker_count=expected_worker_count,
    )
    return evidence


def _task_payload_owner_distribution_evidence(
    task_payloads: tuple[JsonObject, ...],
    expected_worker_count: int | None,
) -> TeamTaskOwnerDistributionEvidence | None:
    """Build task-owner distribution proof from native task payloads.

    Args:
        task_payloads [tuple[JsonObject, ...]]: Native Team task payloads.
        expected_worker_count [int | None]: Expected native worker count.

    Returns:
        TeamTaskOwnerDistributionEvidence | None: Owner distribution proof when
        task payloads are present.
    """
    if not task_payloads:
        missing_evidence: None = None
        return missing_evidence
    owners = tuple(
        owner
        for owner in (
            _string_value(task_payload, "owner") for task_payload in task_payloads
        )
        if owner is not None
    )
    missing_owner_count = len(task_payloads) - len(owners)
    distinct_owner_count = len(frozenset(owners))
    required_distinct_owners = _required_distinct_owner_count(
        task_count=len(task_payloads),
        expected_worker_count=expected_worker_count,
    )
    valid = (
        missing_owner_count == 0
        and distinct_owner_count >= required_distinct_owners
    )
    detail = (
        "Team owner distribution evidence: "
        f"{len(owners)}/{len(task_payloads)} tasks have owners, "
        f"{distinct_owner_count} distinct owners, "
        f"{required_distinct_owners} required distinct owners, "
        f"{missing_owner_count} missing owners."
    )
    if not valid:
        detail = f"{detail} Owner distribution is invalid for company-run Team work."
    evidence = TeamTaskOwnerDistributionEvidence(
        valid=valid,
        task_count=len(task_payloads),
        owner_count=len(owners),
        distinct_owner_count=distinct_owner_count,
        required_distinct_owner_count=required_distinct_owners,
        missing_owner_count=missing_owner_count,
        detail=detail,
    )
    return evidence


def _required_distinct_owner_count(
    task_count: int,
    expected_worker_count: int | None,
) -> int:
    """Return required owner diversity for company-run Team completion.

    Args:
        task_count [int]: Native task count.
        expected_worker_count [int | None]: Expected native worker count.

    Returns:
        int: Minimum distinct owners required.
    """
    if task_count <= 1:
        return task_count
    if expected_worker_count is None or expected_worker_count <= 0:
        required_count = min(2, task_count)
        return required_count
    required_count = min(expected_worker_count, task_count)
    return required_count
