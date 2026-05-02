import asyncio

import orjson

from execution.invoke import run_omx_command
from schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiListTasksSnapshot,
    TeamApiReadEventsRequest,
    TeamApiReadEventsSnapshot,
)
from shared.exceptions.teamwork_exceptions import TeamworkSurfaceError


def _normalize_team_api_payload(stdout: str, operation_name: str) -> dict[str, object]:
    """Normalizes one team-api transport payload into the nested data object.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        dict[str, object]: Nested `data` object from a successful team-api transport payload.

    Raises:
        TeamworkSurfaceError: Raised when the payload is empty, invalid JSON, not a JSON object, reports `ok=false`, or omits the nested data object.
    """
    if not stdout:
        raise TeamworkSurfaceError(f"{operation_name} returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object JSON payload"
        )

    ok_value: object | None = parsed_payload.get("ok")
    if ok_value is not True:
        raise TeamworkSurfaceError(f"{operation_name} returned an unsuccessful payload")

    data_payload: object | None = parsed_payload.get("data")
    if not isinstance(data_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object data payload"
        )

    result: dict[str, object] = data_payload
    return result


async def read_team_api_list_tasks(
    request: TeamApiListTasksRequest,
) -> TeamApiListTasksSnapshot:
    """Reads typed team-api task listings.

    Args:
        request [TeamApiListTasksRequest]: Typed request boundary for `omx team api list-tasks`.

    Returns:
        TeamApiListTasksSnapshot: Normalized list-tasks snapshot built from the nested successful `data` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "list-tasks",
            "--input",
            orjson.dumps({"team_name": request.team_name}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    normalized_payload: dict[str, object] = _normalize_team_api_payload(
        stdout,
        "omx team api list-tasks",
    )
    result: TeamApiListTasksSnapshot = TeamApiListTasksSnapshot.model_validate(
        normalized_payload
    )
    return result


async def read_team_api_read_events(
    request: TeamApiReadEventsRequest,
) -> TeamApiReadEventsSnapshot:
    """Reads typed team-api event listings.

    Args:
        request [TeamApiReadEventsRequest]: Typed request boundary for `omx team api read-events`.

    Returns:
        TeamApiReadEventsSnapshot: Normalized read-events snapshot built from the nested successful `data` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-events",
            "--input",
            orjson.dumps({"team_name": request.team_name}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    normalized_payload: dict[str, object] = _normalize_team_api_payload(
        stdout,
        "omx team api read-events",
    )
    result: TeamApiReadEventsSnapshot = TeamApiReadEventsSnapshot.model_validate(
        normalized_payload
    )
    return result
