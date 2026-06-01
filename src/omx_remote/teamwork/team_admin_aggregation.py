import asyncio
from pathlib import Path

import orjson

from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
    TeamAdminAggregationReportRequest,
)
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiListTasksRequest,
    TeamApiReadEventsRequest,
    TeamApiReadWorkerStatusRequest,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiListTasksSnapshot,
    TeamApiReadEventsSnapshot,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.shared.omx_enums.team_admin_enums import TeamAdminAggregationState
from omx_remote.shared.omx_enums.teamwork_enums import (
    BLOCKED_TASK_STATE_VALUES,
    BLOCKED_WORKER_STATE_VALUES,
    COMPLETED_TASK_STATE_VALUES,
    STARTUP_ISSUE_EVENT_TYPE_VALUES,
    STARTUP_ISSUE_WORKER_STATE_VALUES,
)
from omx_remote.shared.utils.json_file_store import json_file_stores
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
    read_team_api_read_worker_status,
)
from omx_remote.teamwork.team_proof_layers import build_team_proof_layers


def normalize_state_token(state_text: str) -> str:
    """Normalizes external Team status text. Args: state_text. Returns: token."""
    normalized_state: str = state_text.strip().lower().replace("-", "_")
    return normalized_state


def assigned_worker_ids(ralph_prd_artifact: RalphPrdArtifact) -> tuple[str, ...]:
    """Returns the worker IDs assigned by a Ralph PRD artifact.

    Args:
        ralph_prd_artifact [RalphPrdArtifact]: Typed Ralph PRD artifact with Team assignments.

    Returns:
        tuple[str, ...]: Ordered Team worker IDs from the Ralph PRD artifact.

    Raises:
        ValueError: Raised when the PRD does not carry Team worker assignments.
    """
    assignments = ralph_prd_artifact.team_worker_assignments
    if assignments is None:
        raise ValueError(
            "Team Admin aggregation requires Ralph Team worker assignments."
        )

    worker_ids: tuple[str, ...] = tuple(
        assignment.worker_id for assignment in assignments
    )
    return worker_ids


def read_local_omx_team_startup_issue_workers(
    team_name: str,
    worker_ids: tuple[str, ...],
    logs_dir: Path | None = None,
) -> tuple[str, ...]:
    """Reads local OMX startup timing logs for workers that failed readiness.

    Args:
        team_name [str]: OMX Team name whose logs should be scanned.
        worker_ids [tuple[str, ...]]: Ralph-assigned workers eligible for classification.
        logs_dir [Path | None]: Optional OMX logs directory override.

    Returns:
        tuple[str, ...]: Ordered workers with local `ready_wait_end` startup failure evidence.
    """
    candidate_logs_dir: Path = (
        Path.cwd() / ".omx" / "logs" if logs_dir is None else logs_dir
    )
    if not candidate_logs_dir.exists():
        return ()

    worker_id_set: set[str] = set(worker_ids)
    startup_issue_workers: list[str] = []
    for log_path in sorted(candidate_logs_dir.glob("team-delivery-*.jsonl")):
        for line in log_path.read_bytes().splitlines():
            try:
                payload = orjson.loads(line)
            except orjson.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("team") != team_name:
                continue
            if payload.get("event") != "dispatch_result":
                continue
            if payload.get("phase") != "ready_wait_end":
                continue
            if payload.get("result") != "failed":
                continue
            worker_value: object | None = payload.get(
                "to_worker", payload.get("worker")
            )
            if not isinstance(worker_value, str):
                continue
            if worker_value not in worker_id_set:
                continue
            if worker_value in startup_issue_workers:
                continue
            startup_issue_workers.append(worker_value)

    result: tuple[str, ...] = tuple(startup_issue_workers)
    return result


def worker_has_completed_task(
    worker_id: str,
    task_snapshot: TeamApiListTasksSnapshot,
) -> bool:
    """Checks whether a worker has submitted a completed task result.

    Args:
        worker_id [str]: Ralph-assigned worker ID.
        task_snapshot [TeamApiListTasksSnapshot]: Team API task listing snapshot.

    Returns:
        bool: True when the worker owns at least one completed task.
    """
    for task in task_snapshot.tasks:
        if task.owner != worker_id:
            continue
        task_state: str = normalize_state_token(task.status)
        if task_state in COMPLETED_TASK_STATE_VALUES:
            return True

    return False


def worker_has_blocker(
    worker_id: str,
    task_snapshot: TeamApiListTasksSnapshot,
    worker_statuses: tuple[TeamApiWorkerStatusSnapshot, ...],
) -> bool:
    """Checks task and worker status snapshots for worker blockers.

    Args:
        worker_id [str]: Ralph-assigned worker ID.
        task_snapshot [TeamApiListTasksSnapshot]: Team API task listing snapshot.
        worker_statuses [tuple[TeamApiWorkerStatusSnapshot, ...]]: Team API worker status snapshots.

    Returns:
        bool: True when task or worker state is blocked/failed/cancelled.
    """
    for task in task_snapshot.tasks:
        if task.owner != worker_id:
            continue
        task_state: str = normalize_state_token(task.status)
        if task_state in BLOCKED_TASK_STATE_VALUES:
            return True

    for worker_status in worker_statuses:
        if worker_status.worker != worker_id:
            continue
        worker_state: str = normalize_state_token(worker_status.state)
        if worker_state in BLOCKED_WORKER_STATE_VALUES:
            return True

    return False


def worker_has_startup_issue(
    worker_id: str,
    event_snapshot: TeamApiReadEventsSnapshot,
    worker_statuses: tuple[TeamApiWorkerStatusSnapshot, ...],
) -> bool:
    """Checks whether Team runtime surfaced a worker startup issue.

    Args:
        worker_id [str]: Ralph-assigned worker ID.
        event_snapshot [TeamApiReadEventsSnapshot]: Team API event snapshot.
        worker_statuses [tuple[TeamApiWorkerStatusSnapshot, ...]]: Team API worker status snapshots.

    Returns:
        bool: True when runtime evidence points to worker startup readiness failure.
    """
    for worker_status in worker_statuses:
        if worker_status.worker != worker_id:
            continue
        worker_state: str = normalize_state_token(worker_status.state)
        if worker_state in STARTUP_ISSUE_WORKER_STATE_VALUES:
            return True

    for event in event_snapshot.events:
        if event.worker != worker_id:
            continue
        event_type: str = normalize_state_token(event.type)
        if event_type in STARTUP_ISSUE_EVENT_TYPE_VALUES:
            return True

    return False


def worker_has_task(worker_id: str, task_snapshot: TeamApiListTasksSnapshot) -> bool:
    """Checks for owned Team API tasks. Args: worker_id, task_snapshot. Returns: bool."""
    has_task: bool = any(task.owner == worker_id for task in task_snapshot.tasks)
    return has_task


def build_team_admin_summary(
    completed_count: int,
    blocked_count: int,
    missing_count: int,
    startup_issue_count: int,
    total_count: int,
    aggregation_state: TeamAdminAggregationState,
) -> str:
    """Builds the human-readable Team Admin aggregation summary.

    Args:
        completed_count [int]: Number of workers with completed output.
        blocked_count [int]: Number of workers with blocked output/state.
        missing_count [int]: Number of workers without any task result.
        startup_issue_count [int]: Number of workers with runtime startup issue evidence.
        total_count [int]: Number of Ralph-assigned workers.
        aggregation_state [TeamAdminAggregationState]: Final aggregation state.

    Returns:
        str: Stable summary for Ralph post-Team review.
    """
    if aggregation_state == TeamAdminAggregationState.READY_FOR_RALPH_REVIEW:
        return (
            f"Team Admin collected {completed_count}/{total_count} completed worker results; "
            "ready for Ralph review."
        )

    if aggregation_state == TeamAdminAggregationState.HUMAN_REVIEW_REQUIRED:
        return (
            f"Team Admin found {completed_count} completed, {blocked_count} blocked, "
            f"and {missing_count} missing worker result; human review required."
        )

    if startup_issue_count:
        return (
            f"Team Admin collected {completed_count}/{total_count} completed worker results; "
            f"waiting for {startup_issue_count} startup issue worker to be retried."
        )

    return (
        f"Team Admin collected {completed_count}/{total_count} completed worker results; "
        "waiting for remaining workers."
    )


def build_team_admin_aggregation_report(
    ralph_prd_artifact: RalphPrdArtifact,
    task_snapshot: TeamApiListTasksSnapshot,
    event_snapshot: TeamApiReadEventsSnapshot,
    worker_statuses: tuple[TeamApiWorkerStatusSnapshot, ...],
    local_startup_issue_workers: tuple[str, ...] = (),
) -> TeamAdminAggregationReport:
    """Builds Ralph-facing Team Admin aggregation report from Team API snapshots.

    Args:
        ralph_prd_artifact [RalphPrdArtifact]: Ralph PRD artifact containing Team Admin policy.
        task_snapshot [TeamApiListTasksSnapshot]: Team API task listing snapshot.
        event_snapshot [TeamApiReadEventsSnapshot]: Team API event listing snapshot.
        worker_statuses [tuple[TeamApiWorkerStatusSnapshot, ...]]: Worker status snapshots collected by Team Admin.
        local_startup_issue_workers [tuple[str, ...]]: Workers with local OMX startup log failure evidence.

    Returns:
        TeamAdminAggregationReport: Final aggregation report for Ralph post-Team review.

    Raises:
        ValueError: Raised when the Ralph PRD artifact does not carry Team Admin policy.
    """
    team_admin = ralph_prd_artifact.team_admin
    if team_admin is None:
        raise ValueError("Team Admin aggregation requires Ralph team_admin policy.")

    worker_ids: tuple[str, ...] = assigned_worker_ids(ralph_prd_artifact)
    local_startup_issue_worker_set: set[str] = set(local_startup_issue_workers)
    completed_workers: list[str] = []
    missing_workers: list[str] = []
    blocked_workers: list[str] = []
    startup_issue_workers: list[str] = []
    incomplete_workers: list[str] = []

    for worker_id in worker_ids:
        has_task: bool = worker_has_task(worker_id, task_snapshot)
        has_blocker: bool = worker_has_blocker(
            worker_id, task_snapshot, worker_statuses
        )
        has_startup_issue: bool = (not has_task) and (
            worker_id in local_startup_issue_worker_set
            or worker_has_startup_issue(
                worker_id,
                event_snapshot,
                worker_statuses,
            )
        )
        has_completed_task: bool = worker_has_completed_task(worker_id, task_snapshot)

        if has_startup_issue:
            startup_issue_workers.append(worker_id)
        elif not has_task:
            missing_workers.append(worker_id)
        if has_blocker:
            blocked_workers.append(worker_id)
        if has_completed_task and not has_blocker:
            completed_workers.append(worker_id)
        else:
            incomplete_workers.append(worker_id)

    requires_human_review: bool = bool(missing_workers or blocked_workers)
    all_workers_completed: bool = len(completed_workers) == len(worker_ids)
    if requires_human_review:
        aggregation_state = TeamAdminAggregationState.HUMAN_REVIEW_REQUIRED
    elif all_workers_completed:
        aggregation_state = TeamAdminAggregationState.READY_FOR_RALPH_REVIEW
    else:
        aggregation_state = TeamAdminAggregationState.WAITING_FOR_WORKERS

    merge_ready: bool = (
        aggregation_state == TeamAdminAggregationState.READY_FOR_RALPH_REVIEW
    )
    requires_llm_review: bool = team_admin.final_report_required and bool(
        team_admin.requires_llm_review_for
    )
    summary: str = build_team_admin_summary(
        len(completed_workers),
        len(blocked_workers),
        len(missing_workers),
        len(startup_issue_workers),
        len(worker_ids),
        aggregation_state,
    )

    initial_report = TeamAdminAggregationReport(
        admin_id=team_admin.admin_id,
        aggregation_state=aggregation_state,
        merge_ready=merge_ready,
        final_report_required=team_admin.final_report_required,
        completed_workers=tuple(completed_workers),
        missing_workers=tuple(missing_workers),
        blocked_workers=tuple(blocked_workers),
        startup_issue_workers=tuple(startup_issue_workers),
        incomplete_workers=tuple(incomplete_workers),
        requires_human_review=requires_human_review,
        requires_llm_review=requires_llm_review,
        task_count=task_snapshot.count,
        event_count=event_snapshot.count,
        summary=summary,
    )
    proof_layers = build_team_proof_layers(initial_report)
    report: TeamAdminAggregationReport = initial_report.model_copy(
        update={"proof_layers": proof_layers}
    )
    return report


async def read_team_admin_aggregation_report(
    request: TeamAdminAggregationReportRequest,
) -> TeamAdminAggregationReport:
    """Collects Team API snapshots and builds a Ralph-facing aggregation report.

    Args:
        request [TeamAdminAggregationReportRequest]: Typed Team Admin aggregation read request.

    Returns:
        TeamAdminAggregationReport: Aggregation report built from live Team API snapshots.
    """
    worker_ids: tuple[str, ...] = assigned_worker_ids(request.ralph_prd_artifact)
    task_snapshot, event_snapshot = await asyncio.gather(
        read_team_api_list_tasks(TeamApiListTasksRequest(team_name=request.team_name)),
        read_team_api_read_events(
            TeamApiReadEventsRequest(team_name=request.team_name)
        ),
    )
    worker_statuses: tuple[TeamApiWorkerStatusSnapshot, ...] = tuple(
        await asyncio.gather(
            *(
                read_team_api_read_worker_status(
                    TeamApiReadWorkerStatusRequest(
                        team_name=request.team_name,
                        worker=worker_id,
                    )
                )
                for worker_id in worker_ids
            )
        )
    )
    local_startup_issue_workers: tuple[str, ...] = (
        read_local_omx_team_startup_issue_workers(
            request.team_name,
            worker_ids,
        )
    )
    report: TeamAdminAggregationReport = build_team_admin_aggregation_report(
        request.ralph_prd_artifact,
        task_snapshot,
        event_snapshot,
        worker_statuses,
        local_startup_issue_workers,
    )
    return report


def write_team_admin_aggregation_report_artifact(
    report: TeamAdminAggregationReport,
    output_path: Path,
) -> Path:
    """Writes a Team Admin aggregation report JSON artifact.

    Args:
        report [TeamAdminAggregationReport]: Typed aggregation report to persist.
        output_path [Path]: Destination JSON artifact path.

    Returns:
        Path: Destination path that was written.
    """
    json_file_stores.for_path(output_path).write_model(
        report,
        trailing_newline=True,
    )
    written_path: Path = output_path
    return written_path
