from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import msgspec
import orjson

from omx_remote.adapter_types.teams_type.team_api_control_payloads import (
    TeamApiCreateTaskPayload,
)
from omx_remote.runtime.commands.execution.subprocess_attempt_runner import (
    SubprocessAttemptOutcome,
    run_subprocess,
)
from omx_remote.runtime.company_run.artifacts.artifact_writers import write_company_json
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunWorkerDispatchPayload,
    CompanyRunWorkerDispatchRecord,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunNativeTeamListTasksRequest,
    CompanyRunNativeTeamTaskListResponse,
    CompanyRunOwnerTaskInjectionEvidence,
    CompanyRunOwnerTaskInjectionTaskRecord,
)
from omx_remote.shared.utils.json_model_dump import model_json_object


@dataclass(frozen=True)
class CompanyRunInjectedOwnerTask:
    """One owner-aware Team task injected through the OMX Team API."""

    worker: str
    task_id: str
    owner: str
    subject: str


@dataclass(frozen=True)
class CompanyRunOwnerTaskInjectionResult:
    """Result of adapter-owned owner-preserving Team task injection."""

    outcomes: tuple[SubprocessAttemptOutcome, ...]
    tasks: tuple[CompanyRunInjectedOwnerTask, ...]
    verified: bool
    detail: str


def build_owner_injection_bootstrap_task(
    objective: str,
    company_root: Path,
    worker_count: int,
) -> str:
    """Build the initial Team task used before owner-aware API task injection.

    Args:
        objective [str]: Company-run objective.
        company_root [Path]: Company-run artifact root.
        worker_count [int]: Requested worker count.

    Returns:
        str: Native Team bootstrap task.
    """
    task = (
        "company-run owner-preserving bootstrap. "
        f"Objective: {objective}\n\n"
        f"Requested workers: {worker_count}. Do not implement from this bootstrap "
        "task alone. Wait for owner-specific tasks created through `omx team api "
        "create-task` from the company-run adapter. Each worker must work only on "
        "the task whose owner matches its worker id.\n\n"
        f"Read company-run artifacts under `{company_root}` after your owned task "
        "appears. Preserve worker ownership, blockers, and verification evidence."
    )
    return task


def inject_owner_tasks_for_company_run_team(
    cwd: Path,
    team_name: str,
    dispatch_path: Path,
    company_root: Path,
    timeout_seconds: float,
) -> CompanyRunOwnerTaskInjectionResult:
    """Create one owner-aware Team task per company-run dispatch worker.

    Args:
        cwd [Path]: Target repository cwd.
        team_name [str]: Native OMX Team name.
        dispatch_path [Path]: company-run worker-dispatches.json path.
        company_root [Path]: Company-run artifact root.
        timeout_seconds [float]: Subprocess timeout.

    Returns:
        CompanyRunOwnerTaskInjectionResult: Injection attempts and verification.
    """
    dispatch_payload = CompanyRunWorkerDispatchPayload.model_validate_json(
        dispatch_path.read_text(encoding="utf-8")
    )
    outcomes: list[SubprocessAttemptOutcome] = []
    injected_tasks: list[CompanyRunInjectedOwnerTask] = []
    for worker in dispatch_payload.workers:
        subject = _owner_task_subject(worker=worker)
        create_payload = TeamApiCreateTaskPayload(
            team_name=team_name,
            subject=subject,
            description=_owner_task_description(
                worker=worker,
                company_root=company_root,
                dispatch_path=dispatch_path,
            ),
            owner=worker.worker,
            requires_code_change=True,
        )
        create_outcome = run_subprocess(
            argv=(
                "omx",
                "team",
                "api",
                "create-task",
                "--input",
                _json_payload_for_msgspec_payload(create_payload),
                "--json",
            ),
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        outcomes.append(create_outcome)
        created_task = _created_task_from_outcome(
            worker=worker,
            subject=subject,
            outcome=create_outcome,
        )
        if created_task is not None:
            injected_tasks.append(created_task)

    list_payload = CompanyRunNativeTeamListTasksRequest(team_name=team_name)
    list_outcome = run_subprocess(
        argv=(
            "omx",
            "team",
                "api",
                "list-tasks",
                "--input",
                orjson.dumps(model_json_object(list_payload)).decode(),
                "--json",
            ),
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )
    outcomes.append(list_outcome)
    verified, detail = _verify_owner_distribution(
        dispatch_payload=dispatch_payload,
        injected_tasks=tuple(injected_tasks),
        list_outcome=list_outcome,
    )
    result = CompanyRunOwnerTaskInjectionResult(
        outcomes=tuple(outcomes),
        tasks=tuple(injected_tasks),
        verified=verified,
        detail=detail,
    )
    return result


def write_owner_task_injection_evidence(
    company_root: Path,
    team_name: str,
    dispatch_path: Path,
    injection_result: CompanyRunOwnerTaskInjectionResult,
) -> Path:
    """Persist owner-aware task injection evidence.

    Args:
        company_root [Path]: Company-run artifact root.
        team_name [str]: Native Team name.
        dispatch_path [Path]: Worker dispatch artifact path.
        injection_result [CompanyRunOwnerTaskInjectionResult]: Injection result.

    Returns:
        Path: Written evidence artifact path.
    """
    injection_evidence_path = company_root / "team" / "owner-task-injection.json"
    injection_evidence = CompanyRunOwnerTaskInjectionEvidence(
        team_name=team_name,
        dispatch_path=str(dispatch_path),
        verified=injection_result.verified,
        detail=injection_result.detail,
        tasks=tuple(
            CompanyRunOwnerTaskInjectionTaskRecord(
                worker=task.worker,
                task_id=task.task_id,
                owner=task.owner,
                subject=task.subject,
            )
            for task in injection_result.tasks
        ),
        attempt_count=len(injection_result.outcomes),
    )
    write_company_json(path=injection_evidence_path, payload=injection_evidence)
    return injection_evidence_path


def _json_payload_for_msgspec_payload(payload: TeamApiCreateTaskPayload) -> str:
    """Serialize one typed Team API payload as JSON text.

    Args:
        payload [TeamApiCreateTaskPayload]: Typed outbound Team API payload.

    Returns:
        str: JSON text for `omx team api --input`.
    """
    payload_json = orjson.dumps(msgspec.to_builtins(payload)).decode()
    return payload_json


def _owner_task_subject(worker: CompanyRunWorkerDispatchRecord) -> str:
    """Build one short owner task subject.

    Args:
        worker [CompanyRunWorkerDispatchRecord]: Worker dispatch record.

    Returns:
        str: Team task subject.
    """
    subject = f"company-run {worker.worker}: {worker.ownership_boundary}"
    return subject


def _owner_task_description(
    worker: CompanyRunWorkerDispatchRecord,
    company_root: Path,
    dispatch_path: Path,
) -> str:
    """Build one owner-specific task description.

    Args:
        worker [CompanyRunWorkerDispatchRecord]: Worker dispatch record.
        company_root [Path]: Company-run artifact root.
        dispatch_path [Path]: Worker dispatch artifact.

    Returns:
        str: Team task description.
    """
    allowed_subagents = ", ".join(worker.allowed_subagents)
    description = (
        f"Owner: {worker.worker}\n"
        f"Ownership boundary: {worker.ownership_boundary}\n"
        f"Recommended reasoning effort: {worker.reasoning_effort}\n"
        f"Reasoning rationale: {worker.reasoning_rationale}\n"
        f"Allowed subagents: {allowed_subagents}\n"
        f"Subagent boundary rule: {worker.subagent_rule}\n\n"
        f"Company-run root: {company_root}\n"
        f"Dispatch artifact: {dispatch_path}\n\n"
        f"Objective:\n{worker.objective}\n\n"
        "Work only inside this owner lane. Preserve blockers and verification "
        "evidence. Do not claim release readiness without integration, review, "
        "security, architecture, and QA evidence."
    )
    return description


def _created_task_from_outcome(
    worker: CompanyRunWorkerDispatchRecord,
    subject: str,
    outcome: SubprocessAttemptOutcome,
) -> CompanyRunInjectedOwnerTask | None:
    """Extract created task identity from one create-task outcome.

    Args:
        worker [CompanyRunWorkerDispatchRecord]: Worker dispatch record.
        subject [str]: Expected subject.
        outcome [SubprocessAttemptOutcome]: create-task outcome.

    Returns:
        CompanyRunInjectedOwnerTask | None: Created task when parseable.
    """
    if outcome.exit_code != 0 or outcome.timed_out:
        no_task: CompanyRunInjectedOwnerTask | None = None
        return no_task
    try:
        decoded: object = orjson.loads(outcome.stdout)
    except orjson.JSONDecodeError:
        invalid_json: CompanyRunInjectedOwnerTask | None = None
        return invalid_json
    if not isinstance(decoded, dict):
        unexpected_payload: CompanyRunInjectedOwnerTask | None = None
        return unexpected_payload
    data = decoded.get("data")
    if not isinstance(data, dict):
        missing_data: CompanyRunInjectedOwnerTask | None = None
        return missing_data
    task = data.get("task")
    if not isinstance(task, dict):
        missing_task: CompanyRunInjectedOwnerTask | None = None
        return missing_task
    raw_task_id = task.get("id")
    raw_owner = task.get("owner")
    if not isinstance(raw_task_id, str) or not isinstance(raw_owner, str):
        missing_identity: CompanyRunInjectedOwnerTask | None = None
        return missing_identity
    created_task = CompanyRunInjectedOwnerTask(
        worker=worker.worker,
        task_id=raw_task_id,
        owner=raw_owner,
        subject=subject,
    )
    return created_task


def _verify_owner_distribution(
    dispatch_payload: CompanyRunWorkerDispatchPayload,
    injected_tasks: tuple[CompanyRunInjectedOwnerTask, ...],
    list_outcome: SubprocessAttemptOutcome,
) -> tuple[bool, str]:
    """Verify injected task owners are present in Team state.

    Args:
        dispatch_payload [CompanyRunWorkerDispatchPayload]: Expected workers.
        injected_tasks [tuple[CompanyRunInjectedOwnerTask, ...]]: Created tasks.
        list_outcome [SubprocessAttemptOutcome]: list-tasks outcome.

    Returns:
        tuple[bool, str]: Verification verdict and detail.
    """
    expected_workers = tuple(worker.worker for worker in dispatch_payload.workers)
    injected_by_worker = {task.worker: task for task in injected_tasks}
    missing_injection = tuple(
        worker for worker in expected_workers if worker not in injected_by_worker
    )
    if missing_injection:
        detail = "Missing owner-aware create-task results for: " + ", ".join(
            missing_injection
        )
        return False, detail
    if list_outcome.exit_code != 0 or list_outcome.timed_out:
        detail = "Owner task injection created tasks, but list-tasks verification failed."
        return False, detail
    try:
        decoded = orjson.loads(list_outcome.stdout)
        task_list = CompanyRunNativeTeamTaskListResponse.model_validate(decoded)
    except (orjson.JSONDecodeError, ValueError) as error:
        detail = f"Owner task injection list-tasks response was invalid: {error}"
        return False, detail
    expected_owner_by_worker = {
        worker.worker: worker.worker for worker in dispatch_payload.workers
    }
    unexpected_create_owners = tuple(
        f"{task.worker}:{task.task_id}->{task.owner}"
        for task in injected_tasks
        if task.owner != expected_owner_by_worker[task.worker]
    )
    if unexpected_create_owners:
        detail = (
            "Owner-aware create-task returned unexpected owners: "
            + ", ".join(unexpected_create_owners)
        )
        return False, detail
    task_owners_by_id = {task.id: task.owner for task in task_list.data.tasks}
    missing_verified: list[str] = []
    for injected_task in injected_tasks:
        owner = task_owners_by_id.get(injected_task.task_id)
        expected_owner = expected_owner_by_worker[injected_task.worker]
        if owner != expected_owner:
            missing_verified.append(
                f"{injected_task.worker}:{injected_task.task_id}->{owner}"
            )
    if missing_verified:
        detail = "Injected owner tasks missing from Team state: " + ", ".join(
            missing_verified
        )
        return False, detail
    detail = "Owner-aware Team task injection verified for: " + ", ".join(
        expected_workers
    )
    return True, detail
