import asyncio

import orjson

from omx_remote.adapter_types.teamwork_types import (
    TeamApiEnvelopePayload,
    TeamApiListTasksNormalizedPayload,
    TeamApiMailboxListNormalizedPayload,
    TeamApiReadEventsNormalizedPayload,
    TeamApiTransportEventPayload,
    TeamApiTransportMailboxMessagePayload,
    TeamApiTransportPayload,
    TeamApiTransportTaskPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiListTasksSnapshot,
    TeamApiMailboxListRequest,
    TeamApiMailboxListSnapshot,
    TeamApiReadEventsRequest,
    TeamApiReadEventsSnapshot,
    TeamApiReadMonitorSnapshot,
    TeamApiReadMonitorSnapshotRequest,
)
from omx_remote.shared.exceptions.teamwork_exceptions import TeamworkSurfaceError


def _validate_count_matches_length(
    operation_name: str,
    count_value: int,
    actual_length: int,
    collection_name: str,
) -> None:
    if count_value != actual_length:
        raise TeamworkSurfaceError(
            f"{operation_name} returned count that does not match {collection_name} length"
        )


def _load_team_api_payload(stdout: str, operation_name: str) -> TeamApiTransportPayload:
    """Loads one team-api transport payload into the nested data object.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        TeamApiTransportPayload: Nested `data` object from a successful team-api transport payload.

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

    envelope_payload: TeamApiEnvelopePayload = {
        "ok": parsed_payload.get("ok"),
        "data": parsed_payload.get("data"),
    }
    ok_value: object | None = envelope_payload.get("ok")
    if ok_value is not True:
        raise TeamworkSurfaceError(f"{operation_name} returned an unsuccessful payload")

    data_payload: object | None = envelope_payload.get("data")
    if not isinstance(data_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object data payload"
        )

    result: TeamApiTransportPayload = {
        "count": data_payload.get("count"),
        "tasks": data_payload.get("tasks"),
        "cursor": data_payload.get("cursor"),
        "events": data_payload.get("events"),
        "worker": data_payload.get("worker"),
        "messages": data_payload.get("messages"),
        "snapshot": data_payload.get("snapshot"),
    }
    return result


def _normalize_team_api_task_payload(task_payload: object) -> TeamApiTransportTaskPayload:
    """Normalizes one raw team-api task item into the typed read-only subset."""

    if not isinstance(task_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api list-tasks returned a non-object task payload"
        )

    normalized_payload: TeamApiTransportTaskPayload = {
        "id": task_payload.get("id"),
        "subject": task_payload.get("subject", task_payload.get("title")),
        "status": task_payload.get("status"),
        "owner": task_payload.get("owner", task_payload.get("assignee")),
    }
    return normalized_payload


def _normalize_team_api_event_payload(event_payload: object) -> TeamApiTransportEventPayload:
    """Normalizes one raw team-api event item into the typed read-only subset."""

    if not isinstance(event_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api read-events returned a non-object event payload"
        )

    normalized_payload: TeamApiTransportEventPayload = {
        "type": event_payload.get("type"),
        "worker": event_payload.get("worker"),
        "task_id": event_payload.get("task_id"),
        "message_id": event_payload.get("message_id"),
    }
    return normalized_payload


def _normalize_team_api_mailbox_message_payload(
    message_payload: object,
) -> TeamApiTransportMailboxMessagePayload:
    """Normalizes one raw team-api mailbox message into the typed read-only subset."""

    if not isinstance(message_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api mailbox-list returned a non-object message payload"
        )

    normalized_payload: TeamApiTransportMailboxMessagePayload = {
        "id": message_payload.get("id"),
        "subject": message_payload.get("subject"),
        "body": message_payload.get("body"),
        "delivered": message_payload.get("delivered"),
    }
    return normalized_payload


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
    data_payload: TeamApiTransportPayload = _load_team_api_payload(
        stdout,
        "omx team api list-tasks",
    )
    raw_tasks: object = data_payload.get("tasks")
    normalized_payload: TeamApiListTasksNormalizedPayload = {
        "count": data_payload.get("count"),
        "tasks": raw_tasks,
    }
    if isinstance(raw_tasks, list):
        normalized_payload["tasks"] = [
            _normalize_team_api_task_payload(task_payload)
            for task_payload in raw_tasks
        ]
    result: TeamApiListTasksSnapshot = TeamApiListTasksSnapshot.model_validate(
        normalized_payload
    )
    _validate_count_matches_length(
        "omx team api list-tasks",
        result.count,
        len(result.tasks),
        "tasks",
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
    data_payload: TeamApiTransportPayload = _load_team_api_payload(
        stdout,
        "omx team api read-events",
    )
    raw_events: object = data_payload.get("events")
    normalized_payload: TeamApiReadEventsNormalizedPayload = {
        "count": data_payload.get("count"),
        "cursor": data_payload.get("cursor"),
        "events": raw_events,
    }
    if isinstance(raw_events, list):
        normalized_payload["events"] = [
            _normalize_team_api_event_payload(event_payload)
            for event_payload in raw_events
        ]
    result: TeamApiReadEventsSnapshot = TeamApiReadEventsSnapshot.model_validate(
        normalized_payload
    )
    _validate_count_matches_length(
        "omx team api read-events",
        result.count,
        len(result.events),
        "events",
    )
    return result


async def read_team_api_mailbox_list(
    request: TeamApiMailboxListRequest,
) -> TeamApiMailboxListSnapshot:
    """Reads typed team-api mailbox listings.

    Args:
        request [TeamApiMailboxListRequest]: Typed request boundary for `omx team api mailbox-list`.

    Returns:
        TeamApiMailboxListSnapshot: Normalized mailbox-list snapshot built from the nested successful `data` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "mailbox-list",
            "--input",
            orjson.dumps(
                {"team_name": request.team_name, "worker": request.worker}
            ).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    data_payload: TeamApiTransportPayload = _load_team_api_payload(
        stdout,
        "omx team api mailbox-list",
    )
    raw_messages: object = data_payload.get("messages")
    normalized_payload: TeamApiMailboxListNormalizedPayload = {
        "worker": data_payload.get("worker"),
        "count": data_payload.get("count"),
        "messages": raw_messages,
    }
    if isinstance(raw_messages, list):
        normalized_payload["messages"] = [
            _normalize_team_api_mailbox_message_payload(message_payload)
            for message_payload in raw_messages
        ]
    result: TeamApiMailboxListSnapshot = TeamApiMailboxListSnapshot.model_validate(
        normalized_payload
    )
    _validate_count_matches_length(
        "omx team api mailbox-list",
        result.count,
        len(result.messages),
        "messages",
    )
    return result


async def read_team_api_read_monitor_snapshot(
    request: TeamApiReadMonitorSnapshotRequest,
) -> TeamApiReadMonitorSnapshot:
    """Reads typed team-api monitor snapshots.

    Args:
        request [TeamApiReadMonitorSnapshotRequest]: Typed request boundary for `omx team api read-monitor-snapshot`.

    Returns:
        TeamApiReadMonitorSnapshot: Normalized read-monitor-snapshot result built from the nested successful `data` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-monitor-snapshot",
            "--input",
            orjson.dumps({"team_name": request.team_name}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    data_payload: TeamApiTransportPayload = _load_team_api_payload(
        stdout,
        "omx team api read-monitor-snapshot",
    )
    normalized_payload: dict[str, object | None] = {
        "snapshot": data_payload.get("snapshot"),
    }
    result: TeamApiReadMonitorSnapshot = TeamApiReadMonitorSnapshot.model_validate(
        normalized_payload
    )
    return result
