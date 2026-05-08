import asyncio

import msgspec
import orjson

from omx_remote.adapter_types.teamwork_types import (
    TeamAwaitEventSpec,
    TeamAwaitNormalizedPayload,
    TeamAwaitSpec,
    TeamAwaitTransportEventPayload,
    TeamAwaitTransportPayload,
    TeamStatusNormalizedPayload,
    TeamStatusSpec,
    TeamStatusTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.teamwork.status_schemas import (
    TeamAwaitRequest,
    TeamAwaitSnapshot,
    TeamStatusRequest,
    TeamStatusSnapshot,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError


async def read_team_status(request: TeamStatusRequest) -> TeamStatusSnapshot:
    """Reads team status through the typed teamwork surface.
    
    Args:
        request [TeamStatusRequest]: Function argument.
    
    Returns:
        TeamStatusSnapshot: Function return value.
    """

    command_result = await asyncio.to_thread(
        run_omx_command,
        ["team", "status", request.team_name, "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: TeamStatusSnapshot = _normalize_team_status(stdout)
    return result


def _load_team_status_transport_payload(stdout: str) -> TeamStatusTransportPayload:
    """Loads one team-status transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        TeamStatusTransportPayload: Function return value.
    """
    if not stdout:
        raise TeamworkSurfaceError("omx team status returned no stdout output")

    try:
        decoded_payload: object = orjson.loads(stdout)
        parsed_payload: TeamStatusSpec = msgspec.convert(
            decoded_payload,
            type=TeamStatusSpec,
        )
    except (orjson.JSONDecodeError, msgspec.ValidationError) as error:
        raise TeamworkSurfaceError(
            "omx team status returned unparseable JSON output"
        ) from error

    if not isinstance(decoded_payload, dict):
        raise TeamworkSurfaceError(
            "omx team status returned a non-object JSON payload"
        )
    if not isinstance(parsed_payload.team_name, str):
        raise TeamworkSurfaceError("omx team status returned a non-string team_name")
    if not isinstance(parsed_payload.status, str):
        raise TeamworkSurfaceError("omx team status returned a non-string status")

    result = TeamStatusTransportPayload(
        team_name=parsed_payload.team_name,
        status=parsed_payload.status,
    )

    result["phase"] = parsed_payload.phase
    if parsed_payload.current_phase is not None:
        result["current_phase"] = parsed_payload.current_phase
    if parsed_payload.dead_workers is not None:
        result["dead_workers"] = parsed_payload.dead_workers
    if parsed_payload.non_reporting_workers is not None:
        result["non_reporting_workers"] = parsed_payload.non_reporting_workers

    return result

def _normalize_team_status(stdout: str) -> TeamStatusSnapshot:
    """Normalizes `omx team status ... --json` stdout into a stable contract.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        TeamStatusSnapshot: Function return value.
    """
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
    """Awaits team status through the typed teamwork surface.
    
    Args:
        request [TeamAwaitRequest]: Function argument.
    
    Returns:
        TeamAwaitSnapshot: Function return value.
    """

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
    """Loads one team-await transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        TeamAwaitTransportPayload: Function return value.
    """
    if not stdout:
        raise TeamworkSurfaceError("omx team await returned no stdout output")

    try:
        decoded_payload: object = orjson.loads(stdout)
        parsed_payload: TeamAwaitSpec = msgspec.convert(
            decoded_payload,
            type=TeamAwaitSpec,
        )
    except (orjson.JSONDecodeError, msgspec.ValidationError) as error:
        raise TeamworkSurfaceError(
            "omx team await returned unparseable JSON output"
        ) from error

    if not isinstance(decoded_payload, dict):
        raise TeamworkSurfaceError(
            "omx team await returned a non-object JSON payload"
        )
    if not isinstance(parsed_payload.team_name, str):
        raise TeamworkSurfaceError("omx team await returned a non-string team_name")
    if not isinstance(parsed_payload.status, str):
        raise TeamworkSurfaceError("omx team await returned a non-string status")

    result = TeamAwaitTransportPayload(
        team_name=parsed_payload.team_name,
        status=parsed_payload.status,
    )

    if isinstance(parsed_payload.cursor, str):
        result["cursor"] = parsed_payload.cursor

    event_spec: TeamAwaitEventSpec | None = parsed_payload.event
    if event_spec is None:
        result["event"] = None
    else:
        normalized_event_payload = TeamAwaitTransportEventPayload()
        if event_spec.type is not None:
            normalized_event_payload["type"] = event_spec.type
        if event_spec.worker is not None:
            normalized_event_payload["worker"] = event_spec.worker
        if event_spec.task_id is not None:
            normalized_event_payload["task_id"] = event_spec.task_id
        result["event"] = normalized_event_payload

    return result

def _normalize_team_await(stdout: str) -> TeamAwaitSnapshot:
    """Normalizes `omx team await ... --json` stdout into a stable contract.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        TeamAwaitSnapshot: Function return value.
    """
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
