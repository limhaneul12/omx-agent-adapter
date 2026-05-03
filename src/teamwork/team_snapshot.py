import asyncio

import orjson

from adapter_types.teamwork_types import (
    TeamAwaitNormalizedPayload,
    TeamAwaitTransportEventPayload,
    TeamAwaitTransportPayload,
    TeamStatusNormalizedPayload,
    TeamStatusTransportPayload,
)
from execution.invoke import run_omx_command
from schemas.teamwork_schemas import (
    TeamAwaitRequest,
    TeamAwaitSnapshot,
    TeamStatusRequest,
    TeamStatusSnapshot,
)
from shared.exceptions.teamwork_exceptions import TeamworkSurfaceError


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

    result: TeamStatusTransportPayload = {
        "team_name": parsed_payload.get("team_name"),
        "status": parsed_payload.get("status"),
        "phase": parsed_payload.get("phase"),
        "current_phase": parsed_payload.get("current_phase"),
        "dead_workers": parsed_payload.get("dead_workers"),
        "non_reporting_workers": parsed_payload.get("non_reporting_workers"),
    }
    return result


def _normalize_team_status(stdout: str) -> TeamStatusSnapshot:
    """Normalizes `omx team status ... --json` stdout into a stable contract."""
    parsed_payload: TeamStatusTransportPayload = _load_team_status_transport_payload(
        stdout
    )

    phase_value: object | None = parsed_payload.get("phase")
    if phase_value is None:
        phase_value = parsed_payload.get("current_phase")

    dead_workers_payload: object | None = parsed_payload.get("dead_workers")
    normalized_dead_workers: object = dead_workers_payload
    if dead_workers_payload is None:
        normalized_dead_workers = []

    non_reporting_workers_payload: object | None = parsed_payload.get(
        "non_reporting_workers"
    )
    normalized_non_reporting_workers: object = non_reporting_workers_payload
    if non_reporting_workers_payload is None:
        normalized_non_reporting_workers = []

    normalized_payload: TeamStatusNormalizedPayload = {
        "team_name": parsed_payload.get("team_name"),
        "status": parsed_payload.get("status"),
        "phase": phase_value,
        "dead_workers": normalized_dead_workers,
        "non_reporting_workers": normalized_non_reporting_workers,
    }
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

    result: TeamAwaitTransportPayload = {
        "team_name": parsed_payload.get("team_name"),
        "status": parsed_payload.get("status"),
        "cursor": parsed_payload.get("cursor"),
        "event": parsed_payload.get("event"),
    }
    return result


def _normalize_team_await(stdout: str) -> TeamAwaitSnapshot:
    """Normalizes `omx team await ... --json` stdout into a stable contract."""
    parsed_payload: TeamAwaitTransportPayload = _load_team_await_transport_payload(
        stdout
    )

    event_payload: object | None = parsed_payload.get("event")
    event_type: str | None = None
    event_worker: str | None = None
    event_task_id: str | None = None
    if isinstance(event_payload, dict):
        normalized_event_payload: TeamAwaitTransportEventPayload = {
            "type": event_payload.get("type"),
            "worker": event_payload.get("worker"),
            "task_id": event_payload.get("task_id"),
        }
        raw_event_type: object | None = normalized_event_payload.get("type")
        if isinstance(raw_event_type, str):
            event_type = raw_event_type
        raw_event_worker: object | None = normalized_event_payload.get("worker")
        if isinstance(raw_event_worker, str):
            event_worker = raw_event_worker
        raw_event_task_id: object | None = normalized_event_payload.get("task_id")
        if isinstance(raw_event_task_id, str):
            event_task_id = raw_event_task_id

    normalized_payload: TeamAwaitNormalizedPayload = {
        "team_name": parsed_payload.get("team_name"),
        "status": parsed_payload.get("status"),
        "cursor": parsed_payload.get("cursor"),
        "event_type": event_type,
        "event_worker": event_worker,
        "event_task_id": event_task_id,
    }
    result: TeamAwaitSnapshot = TeamAwaitSnapshot.model_validate(
        normalized_payload
    )
    return result
