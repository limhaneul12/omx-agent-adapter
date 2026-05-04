import asyncio

import orjson

from omx_remote.adapter_types.teamwork_types import (
    TeamAwaitNormalizedPayload,
    TeamAwaitTransportEventPayload,
    TeamAwaitTransportPayload,
    TeamStatusNormalizedPayload,
    TeamStatusTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.teamwork_schemas import (
    TeamAwaitRequest,
    TeamAwaitSnapshot,
    TeamStatusRequest,
    TeamStatusSnapshot,
)
from omx_remote.shared.exceptions.teamwork_exceptions import TeamworkSurfaceError


async def read_team_status(request: TeamStatusRequest) -> TeamStatusSnapshot:
    """Reads team status through the typed teamwork surface."""

    command_result = await asyncio.to_thread(
        run_omx_command,
        ["team", "status", request.team_name, "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: TeamStatusSnapshot = _normalize_team_status(stdout)
    return result


def _load_team_status_transport_payload(stdout: str) -> TeamStatusTransportPayload:
    """Loads one team-status transport payload from raw stdout."""
    if not stdout:
        raise TeamworkSurfaceError("omx team status returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise TeamworkSurfaceError(
            "omx team status returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise TeamworkSurfaceError(
            "omx team status returned a non-object JSON payload"
        )

    team_name_value: object | None = parsed_payload.get("team_name")
    if not isinstance(team_name_value, str):
        raise TeamworkSurfaceError("omx team status returned a non-string team_name")

    status_value: object | None = parsed_payload.get("status")
    if not isinstance(status_value, str):
        raise TeamworkSurfaceError("omx team status returned a non-string status")

    result = TeamStatusTransportPayload(
        team_name=team_name_value,
        status=status_value,
    )

    phase_value: object | None = parsed_payload.get("phase")
    if phase_value is None or isinstance(phase_value, str):
        result["phase"] = phase_value

    current_phase_value: object | None = parsed_payload.get("current_phase")
    if current_phase_value is None or isinstance(current_phase_value, str):
        result["current_phase"] = current_phase_value

    dead_workers_value: object | None = parsed_payload.get("dead_workers")
    if isinstance(dead_workers_value, list) and all(
        isinstance(worker_name, str) for worker_name in dead_workers_value
    ):
        result["dead_workers"] = dead_workers_value

    non_reporting_workers_value: object | None = parsed_payload.get(
        "non_reporting_workers"
    )
    if isinstance(non_reporting_workers_value, list) and all(
        isinstance(worker_name, str) for worker_name in non_reporting_workers_value
    ):
        result["non_reporting_workers"] = non_reporting_workers_value

    return result


def _normalize_team_status(stdout: str) -> TeamStatusSnapshot:
    """Normalizes `omx team status ... --json` stdout into a stable contract."""
    parsed_payload: TeamStatusTransportPayload = _load_team_status_transport_payload(
        stdout
    )

    phase_value: str | None = parsed_payload.get("phase")
    if phase_value is None:
        phase_value = parsed_payload.get("current_phase")

    dead_workers_payload: list[str] | None = parsed_payload.get("dead_workers")
    normalized_dead_workers: list[str] = []
    if dead_workers_payload is None:
        normalized_dead_workers = []
    else:
        normalized_dead_workers = dead_workers_payload

    non_reporting_workers_payload: list[str] | None = parsed_payload.get(
        "non_reporting_workers"
    )
    normalized_non_reporting_workers: list[str] = []
    if non_reporting_workers_payload is None:
        normalized_non_reporting_workers = []
    else:
        normalized_non_reporting_workers = non_reporting_workers_payload

    normalized_payload = TeamStatusNormalizedPayload(
        team_name=parsed_payload["team_name"],
        status=parsed_payload["status"],
        phase=phase_value,
        dead_workers=normalized_dead_workers,
        non_reporting_workers=normalized_non_reporting_workers,
    )
    result: TeamStatusSnapshot = TeamStatusSnapshot.model_validate(
        normalized_payload
    )
    return result


async def await_team_status(request: TeamAwaitRequest) -> TeamAwaitSnapshot:
    """Awaits team status through the typed teamwork surface."""

    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "await",
            request.team_name,
            "--timeout-ms",
            "1000",
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    result: TeamAwaitSnapshot = _normalize_team_await(stdout)
    return result


def _load_team_await_transport_payload(stdout: str) -> TeamAwaitTransportPayload:
    """Loads one team-await transport payload from raw stdout."""
    if not stdout:
        raise TeamworkSurfaceError("omx team await returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise TeamworkSurfaceError(
            "omx team await returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise TeamworkSurfaceError(
            "omx team await returned a non-object JSON payload"
        )

    team_name_value: object | None = parsed_payload.get("team_name")
    if not isinstance(team_name_value, str):
        raise TeamworkSurfaceError("omx team await returned a non-string team_name")

    status_value: object | None = parsed_payload.get("status")
    if not isinstance(status_value, str):
        raise TeamworkSurfaceError("omx team await returned a non-string status")

    result = TeamAwaitTransportPayload(
        team_name=team_name_value,
        status=status_value,
    )

    cursor_value: object | None = parsed_payload.get("cursor")
    if isinstance(cursor_value, str):
        result["cursor"] = cursor_value

    event_value: object | None = parsed_payload.get("event")
    if event_value is None:
        result["event"] = None
    elif isinstance(event_value, dict):
        normalized_event_payload = TeamAwaitTransportEventPayload()

        event_type_value: object | None = event_value.get("type")
        if isinstance(event_type_value, str):
            normalized_event_payload["type"] = event_type_value

        event_worker_value: object | None = event_value.get("worker")
        if isinstance(event_worker_value, str):
            normalized_event_payload["worker"] = event_worker_value

        event_task_id_value: object | None = event_value.get("task_id")
        if isinstance(event_task_id_value, str):
            normalized_event_payload["task_id"] = event_task_id_value

        result["event"] = normalized_event_payload

    return result


def _normalize_team_await(stdout: str) -> TeamAwaitSnapshot:
    """Normalizes `omx team await ... --json` stdout into a stable contract."""
    parsed_payload: TeamAwaitTransportPayload = _load_team_await_transport_payload(
        stdout
    )

    cursor_payload: str | None = parsed_payload.get("cursor")
    normalized_cursor: str | None = cursor_payload
    if cursor_payload == "":
        normalized_cursor = None

    event_payload: TeamAwaitTransportEventPayload | None = parsed_payload.get("event")
    event_type: str | None = None
    event_worker: str | None = None
    event_task_id: str | None = None
    if isinstance(event_payload, dict):
        event_type = event_payload.get("type")
        event_worker = event_payload.get("worker")
        event_task_id = event_payload.get("task_id")

    normalized_payload = TeamAwaitNormalizedPayload(
        team_name=parsed_payload["team_name"],
        status=parsed_payload["status"],
        cursor=normalized_cursor,
        event_type=event_type,
        event_worker=event_worker,
        event_task_id=event_task_id,
    )
    result: TeamAwaitSnapshot = TeamAwaitSnapshot.model_validate(
        normalized_payload
    )
    return result
