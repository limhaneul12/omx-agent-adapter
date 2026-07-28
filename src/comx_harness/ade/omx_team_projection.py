from __future__ import annotations

from comx_harness.schemas.omx_team_schemas import (
    OmxNativeMonitorSnapshot,
    OmxNativeSummaryWorker,
    OmxNativeTask,
    OmxNativeTeamConfig,
    OmxNativeTeamSummary,
    OmxTaskProjection,
    OmxTeamProjection,
    OmxWorkerProjection,
)
from comx_harness.shared.harness_enums.operator_enums import AgentStatus


def project_omx_team(
    *,
    status: str,
    config: OmxNativeTeamConfig,
    tasks: tuple[OmxNativeTask, ...],
    summary: OmxNativeTeamSummary | None,
    monitor: OmxNativeMonitorSnapshot | None,
) -> OmxTeamProjection:
    summary_workers = {item.name: item for item in summary.workers} if summary else {}
    non_reporting = summary.non_reporting_workers if summary else ()
    workers: list[OmxWorkerProjection] = []
    for native in config.workers:
        summary_worker = summary_workers.get(native.name)
        state = _agent_status(
            monitor.worker_state_by_name.get(native.name) if monitor else None
        )
        alive = _worker_alive(native.name, summary_worker, monitor)
        current_task = (
            monitor.worker_task_id_by_name.get(native.name) if monitor else None
        )
        turns = summary_worker.turns_without_progress if summary_worker else 0
        workers.append(
            OmxWorkerProjection(
                name=native.name,
                role=native.role,
                state=state,
                alive=alive,
                current_task_id=current_task,
                pane_id=native.pane_id,
                working_dir=native.working_dir,
                worktree_path=native.worktree_path,
                worktree_branch=native.worktree_branch,
                last_turn_at=summary_worker.last_turn_at if summary_worker else None,
                turns_without_progress=turns,
                attention=_worker_attention(
                    state=state,
                    alive=alive,
                    non_reporting=native.name in non_reporting,
                    turns_without_progress=turns,
                ),
            )
        )
    projected_tasks = tuple(_project_task(task) for task in tasks)
    attention = list(non_reporting)
    attention.extend(
        f"task {task.task_id} is {task.status}"
        for task in projected_tasks
        if task.status in {"blocked", "failed"}
    )
    attention.extend(
        f"worker {worker.name}: {message}"
        for worker in workers
        for message in worker.attention
    )
    return OmxTeamProjection(
        team_name=config.name,
        status=status,
        available=True,
        detail=f"Native OMX Team API: {len(workers)} workers, {len(projected_tasks)} tasks.",
        task=config.task,
        tmux_session=config.tmux_session,
        leader_pane_id=config.leader_pane_id,
        workspace_mode=config.workspace_mode,
        workers=tuple(workers),
        tasks=projected_tasks,
        non_reporting_workers=non_reporting,
        attention=tuple(attention),
    )


def unavailable_omx_team(team_name: str, detail: str) -> OmxTeamProjection:
    return OmxTeamProjection(
        team_name=team_name,
        status="unavailable",
        available=False,
        detail=detail,
    )


def build_omx_attach_argv(
    team: OmxTeamProjection,
    *,
    inside_tmux: bool,
    worker_name: str | None = None,
) -> tuple[str, ...]:
    if not team.tmux_session:
        raise ValueError("OMX team has no tmux session identity")
    action = "switch-client" if inside_tmux else "attach-session"
    argv: tuple[str, ...] = ("tmux", action, "-t", team.tmux_session)
    if worker_name is None:
        return argv
    worker = next((item for item in team.workers if item.name == worker_name), None)
    if worker is None or not worker.pane_id:
        raise ValueError(f"worker has no attachable pane: {worker_name}")
    return (*argv, ";", "select-pane", "-t", worker.pane_id)


def _worker_alive(
    name: str,
    summary_worker: OmxNativeSummaryWorker | None,
    monitor: OmxNativeMonitorSnapshot | None,
) -> bool | None:
    if monitor and name in monitor.worker_alive_by_name:
        return monitor.worker_alive_by_name[name]
    return summary_worker.alive if summary_worker else None


def _project_task(task: OmxNativeTask) -> OmxTaskProjection:
    return OmxTaskProjection(
        task_id=task.id,
        subject=task.subject,
        status=task.status,
        owner=task.owner,
        role=task.role,
        blocked_by=task.blocked_by,
        error=task.error,
    )


def _agent_status(value: str | None) -> AgentStatus:
    if value is None:
        return AgentStatus.UNKNOWN
    try:
        return AgentStatus(value)
    except ValueError:
        return AgentStatus.UNKNOWN


def _worker_attention(
    *,
    state: AgentStatus,
    alive: bool | None,
    non_reporting: bool,
    turns_without_progress: int,
) -> tuple[str, ...]:
    messages: list[str] = []
    if state in {AgentStatus.BLOCKED, AgentStatus.FAILED}:
        messages.append(f"state={state}")
    if alive is False:
        messages.append("heartbeat is not alive")
    if non_reporting:
        messages.append("worker is not reporting")
    if turns_without_progress > 0:
        messages.append(f"{turns_without_progress} turns without progress")
    return tuple(messages)
