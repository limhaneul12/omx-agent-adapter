import asyncio

import orjson

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


def _normalize_team_status(stdout: str) -> TeamStatusSnapshot:
    """Normalizes `omx team status ... --json` stdout into a stable contract."""

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

    phase_value: object | None = parsed_payload.get("phase")
    if phase_value is None:
        phase_value = parsed_payload.get("current_phase")
    normalized_payload: dict[str, object] = {
        "team_name": parsed_payload.get("team_name"),
        "status": parsed_payload.get("status"),
        "phase": phase_value,
        "dead_workers": parsed_payload.get("dead_workers", []),
        "non_reporting_workers": parsed_payload.get(
            "non_reporting_workers",
            [],
        ),
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


def _normalize_team_await(stdout: str) -> TeamAwaitSnapshot:
    """Normalizes `omx team await ... --json` stdout into a stable contract."""

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

    event_payload: object | None = parsed_payload.get("event")
    event_type: str | None = None
    event_worker: str | None = None
    event_task_id: str | None = None
    if isinstance(event_payload, dict):
        raw_event_type: object | None = event_payload.get("type")
        if isinstance(raw_event_type, str):
            event_type = raw_event_type
        raw_event_worker: object | None = event_payload.get("worker")
        if isinstance(raw_event_worker, str):
            event_worker = raw_event_worker
        raw_event_task_id: object | None = event_payload.get("task_id")
        if isinstance(raw_event_task_id, str):
            event_task_id = raw_event_task_id

    normalized_payload: dict[str, object] = {
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
