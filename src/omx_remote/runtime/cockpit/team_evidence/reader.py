import asyncio

from omx_remote.runtime.cockpit.team_evidence.proof_layers import (
    build_cockpit_team_observation_proof_layers,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitTeamObservation,
    CockpitTeamWorkerObservation,
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
from omx_remote.schemas.teamwork.status_schemas import (
    TeamStatusRequest,
    TeamStatusSnapshot,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.teamwork.team_api_snapshot import (
    read_team_api_list_tasks,
    read_team_api_read_events,
    read_team_api_read_worker_status,
)
from omx_remote.teamwork.team_snapshot import read_team_status


async def _read_team_observations(
    team_names: tuple[str, ...],
) -> tuple[CockpitTeamObservation, ...]:
    """Read explicit Team evidence for the cockpit.

    Args:
        team_names [tuple[str, ...]]: Team names requested by the caller.

    Returns:
        tuple[CockpitTeamObservation, ...]: Team evidence snapshots in caller order.
    """
    if not team_names:
        empty_observations: tuple[CockpitTeamObservation, ...] = ()
        return empty_observations

    observation_tasks = [
        asyncio.create_task(_read_team_observation(team_name)) for team_name in team_names
    ]
    observations_list: list[CockpitTeamObservation] = list(await asyncio.gather(*observation_tasks))
    observations: tuple[CockpitTeamObservation, ...] = tuple(observations_list)
    return observations


async def _read_team_observation(team_name: str) -> CockpitTeamObservation:
    """Read one Team's status, tasks, events, and worker statuses.

    Args:
        team_name [str]: Team name to inspect through read-only Team surfaces.

    Returns:
        CockpitTeamObservation: Aggregated Team evidence for the cockpit.
    """
    warnings: list[str] = []
    status_snapshot: TeamStatusSnapshot | None = None
    tasks_snapshot: TeamApiListTasksSnapshot | None = None
    events_snapshot: TeamApiReadEventsSnapshot | None = None

    try:
        status_snapshot = await read_team_status(TeamStatusRequest(team_name=team_name))
    except TeamworkSurfaceError as error:
        warnings.append(f"team status read failed for {team_name}: {error}")

    try:
        tasks_snapshot = await read_team_api_list_tasks(
            TeamApiListTasksRequest(team_name=team_name)
        )
    except TeamworkSurfaceError as error:
        warnings.append(f"team task read failed for {team_name}: {error}")

    try:
        events_snapshot = await read_team_api_read_events(
            TeamApiReadEventsRequest(team_name=team_name)
        )
    except TeamworkSurfaceError as error:
        warnings.append(f"team event read failed for {team_name}: {error}")

    worker_names: tuple[str, ...] = _derive_observed_worker_names(
        status_snapshot=status_snapshot,
        tasks_snapshot=tasks_snapshot,
        events_snapshot=events_snapshot,
    )
    worker_statuses: tuple[CockpitTeamWorkerObservation, ...] = await _read_team_worker_observations(
        team_name=team_name,
        worker_names=worker_names,
        warnings=warnings,
    )

    status_value: str = "unknown"
    phase_value: str | None = None
    if status_snapshot is not None:
        status_value = status_snapshot.status
        phase_value = status_snapshot.phase

    task_count: int = 0
    if tasks_snapshot is not None:
        task_count = tasks_snapshot.count

    event_count: int = 0
    if events_snapshot is not None:
        event_count = events_snapshot.count

    base_observation = CockpitTeamObservation(
        team_name=team_name,
        status=status_value,
        phase=phase_value,
        task_count=task_count,
        event_count=event_count,
        worker_statuses=worker_statuses,
        warnings=tuple(warnings),
    )
    proof_layers = build_cockpit_team_observation_proof_layers(base_observation)
    observation: CockpitTeamObservation = base_observation.model_copy(
        update={"proof_layers": proof_layers}
    )
    return observation

def _derive_observed_worker_names(
    status_snapshot: TeamStatusSnapshot | None,
    tasks_snapshot: TeamApiListTasksSnapshot | None,
    events_snapshot: TeamApiReadEventsSnapshot | None,
) -> tuple[str, ...]:
    """Derive worker names worth probing from Team status/task/event evidence.

    Args:
        status_snapshot [TeamStatusSnapshot | None]: Optional Team status evidence.
        tasks_snapshot [TeamApiListTasksSnapshot | None]: Optional Team task evidence.
        events_snapshot [TeamApiReadEventsSnapshot | None]: Optional Team event evidence.

    Returns:
        tuple[str, ...]: Stable ordered unique worker names.
    """
    worker_names: list[str] = []
    seen_worker_names: set[str] = set()

    if status_snapshot is not None:
        for worker_name in (*status_snapshot.dead_workers, *status_snapshot.non_reporting_workers):
            if worker_name not in seen_worker_names:
                seen_worker_names.add(worker_name)
                worker_names.append(worker_name)

    if tasks_snapshot is not None:
        for task_snapshot in tasks_snapshot.tasks:
            if task_snapshot.owner is not None and task_snapshot.owner not in seen_worker_names:
                seen_worker_names.add(task_snapshot.owner)
                worker_names.append(task_snapshot.owner)

    if events_snapshot is not None:
        for event_snapshot in events_snapshot.events:
            if event_snapshot.worker is not None and event_snapshot.worker not in seen_worker_names:
                seen_worker_names.add(event_snapshot.worker)
                worker_names.append(event_snapshot.worker)

    result: tuple[str, ...] = tuple(worker_names)
    return result

async def _read_team_worker_observations(
    team_name: str,
    worker_names: tuple[str, ...],
    warnings: list[str],
) -> tuple[CockpitTeamWorkerObservation, ...]:
    """Read worker-status snapshots for observed Team workers.

    Args:
        team_name [str]: Team name owning the workers.
        worker_names [tuple[str, ...]]: Worker names to inspect.
        warnings [list[str]]: Mutable warning collection for read failures.

    Returns:
        tuple[CockpitTeamWorkerObservation, ...]: Worker status observations.
    """
    worker_observations: list[CockpitTeamWorkerObservation] = []
    for worker_name in worker_names:
        try:
            worker_status: TeamApiWorkerStatusSnapshot = await read_team_api_read_worker_status(
                TeamApiReadWorkerStatusRequest(team_name=team_name, worker=worker_name)
            )
        except TeamworkSurfaceError as error:
            warnings.append(
                f"team worker-status read failed for {team_name}/{worker_name}: {error}"
            )
            continue

        worker_observation = CockpitTeamWorkerObservation(
            worker=worker_status.worker,
            state=worker_status.state,
            updated_at=worker_status.updated_at,
        )
        worker_observations.append(worker_observation)

    result: tuple[CockpitTeamWorkerObservation, ...] = tuple(worker_observations)
    return result
