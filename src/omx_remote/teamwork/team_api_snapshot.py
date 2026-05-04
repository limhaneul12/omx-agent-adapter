import asyncio

import orjson

from omx_remote.adapter_types.teamwork_types import (
    TeamApiEnvelopePayload,
    TeamApiErrorTransportPayload,
    TeamApiListTasksNormalizedPayload,
    TeamApiMailboxListNormalizedPayload,
    TeamApiReadEventsNormalizedPayload,
    TeamApiTransportEventPayload,
    TeamApiTransportMailboxMessagePayload,
    TeamApiTransportPayload,
    TeamApiTransportTaskPayload,
    TeamApiTransportWorkerStatusPayload,
    TeamApiWorkerStatusNormalizedPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.teamwork_schemas import (
    TeamApiListTasksRequest,
    TeamApiListTasksSnapshot,
    TeamApiMailboxListRequest,
    TeamApiMailboxListSnapshot,
    TeamApiReadConfigError,
    TeamApiReadConfigRequest,
    TeamApiReadConfigSnapshot,
    TeamApiReadEventsRequest,
    TeamApiReadEventsSnapshot,
    TeamApiReadManifestError,
    TeamApiReadManifestRequest,
    TeamApiReadMonitorSnapshot,
    TeamApiReadMonitorSnapshotRequest,
    TeamApiReadWorkerStatusRequest,
    TeamApiWorkerStatusSnapshot,
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

    ok_value: object | None = parsed_payload.get("ok")
    if ok_value is not True:
        raise TeamworkSurfaceError(f"{operation_name} returned an unsuccessful payload")

    envelope_payload: TeamApiEnvelopePayload = {
        "ok": True,
        "data": parsed_payload.get("data"),
    }

    data_payload: object | None = envelope_payload.get("data")
    if not isinstance(data_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object data payload"
        )

    result: TeamApiTransportPayload = {}

    count_value: object | None = data_payload.get("count")
    if isinstance(count_value, int):
        result["count"] = count_value

    cursor_value: object | None = data_payload.get("cursor")
    if isinstance(cursor_value, str):
        result["cursor"] = cursor_value

    worker_value: object | None = data_payload.get("worker")
    if isinstance(worker_value, str):
        result["worker"] = worker_value

    result["tasks"] = data_payload.get("tasks")
    result["events"] = data_payload.get("events")
    result["messages"] = data_payload.get("messages")
    result["snapshot"] = data_payload.get("snapshot")
    result["status"] = data_payload.get("status")
    result["config"] = data_payload.get("config")
    result["manifest"] = data_payload.get("manifest")
    return result


def _load_team_api_error_payload(stdout: str, operation_name: str) -> TeamApiErrorTransportPayload:
    """Loads one team-api transport payload into the nested error object.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        TeamApiErrorTransportPayload: Narrow error payload containing only the stable `code` and `message` fields.

    Raises:
        TeamworkSurfaceError: Raised when the payload is empty, invalid JSON, not a JSON object, reports `ok=true`, or omits the nested error object.
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
    if ok_value is not False:
        raise TeamworkSurfaceError(f"{operation_name} returned a successful payload")

    error_payload: object | None = parsed_payload.get("error")
    if not isinstance(error_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object error payload"
        )

    code_value: object | None = error_payload.get("code")
    if not isinstance(code_value, str):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-string error code"
        )

    message_value: object | None = error_payload.get("message")
    if not isinstance(message_value, str):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-string error message"
        )

    result: TeamApiErrorTransportPayload = {
        "code": code_value,
        "message": message_value,
    }
    return result


def _normalize_team_api_task_payload(task_payload: object) -> TeamApiTransportTaskPayload:
    """Normalizes one raw team-api task item into the typed read-only subset."""

    if not isinstance(task_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api list-tasks returned a non-object task payload"
        )

    normalized_payload: TeamApiTransportTaskPayload = {}

    id_value: object | None = task_payload.get("id")
    if isinstance(id_value, str):
        normalized_payload["id"] = id_value

    subject_value: object | None = task_payload.get("subject", task_payload.get("title"))
    if isinstance(subject_value, str):
        normalized_payload["subject"] = subject_value

    status_value: object | None = task_payload.get("status")
    if isinstance(status_value, str):
        normalized_payload["status"] = status_value

    owner_value: object | None = task_payload.get("owner", task_payload.get("assignee"))
    if isinstance(owner_value, str):
        normalized_payload["owner"] = owner_value

    return normalized_payload


def _normalize_team_api_event_payload(event_payload: object) -> TeamApiTransportEventPayload:
    """Normalizes one raw team-api event item into the typed read-only subset."""

    if not isinstance(event_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api read-events returned a non-object event payload"
        )

    normalized_payload: TeamApiTransportEventPayload = {}

    type_value: object | None = event_payload.get("type")
    if isinstance(type_value, str):
        normalized_payload["type"] = type_value

    worker_value: object | None = event_payload.get("worker")
    if isinstance(worker_value, str):
        normalized_payload["worker"] = worker_value

    task_id_value: object | None = event_payload.get("task_id")
    if isinstance(task_id_value, str):
        normalized_payload["task_id"] = task_id_value

    message_id_value: object | None = event_payload.get("message_id")
    if message_id_value is None or isinstance(message_id_value, str):
        normalized_payload["message_id"] = message_id_value

    return normalized_payload


def _normalize_team_api_mailbox_message_payload(
    message_payload: object,
) -> TeamApiTransportMailboxMessagePayload:
    """Normalizes one raw team-api mailbox message into the typed read-only subset."""

    if not isinstance(message_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api mailbox-list returned a non-object message payload"
        )

    normalized_payload: TeamApiTransportMailboxMessagePayload = {}

    id_value: object | None = message_payload.get("id")
    if isinstance(id_value, str):
        normalized_payload["id"] = id_value

    subject_value: object | None = message_payload.get("subject")
    if isinstance(subject_value, str):
        normalized_payload["subject"] = subject_value

    body_value: object | None = message_payload.get("body")
    if isinstance(body_value, str):
        normalized_payload["body"] = body_value

    delivered_value: object | None = message_payload.get("delivered")
    if isinstance(delivered_value, bool):
        normalized_payload["delivered"] = delivered_value

    return normalized_payload


def _normalize_team_api_worker_status_payload(
    worker_name: object,
    status_payload: object,
) -> TeamApiWorkerStatusSnapshot:
    """Normalizes one raw team-api worker-status payload into the typed subset."""

    if not isinstance(status_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api read-worker-status returned a non-object status payload"
        )

    normalized_status_payload: TeamApiTransportWorkerStatusPayload = {}

    state_value: object | None = status_payload.get("state")
    if isinstance(state_value, str):
        normalized_status_payload["state"] = state_value

    updated_at_value: object | None = status_payload.get("updated_at")
    if isinstance(updated_at_value, str):
        normalized_status_payload["updated_at"] = updated_at_value

    return TeamApiWorkerStatusSnapshot.model_validate(
        {
            "worker": worker_name,
            "state": normalized_status_payload.get("state"),
            "updated_at": normalized_status_payload.get("updated_at"),
        }
    )


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
    count_value: int | None = data_payload.get("count")
    normalized_payload: TeamApiListTasksNormalizedPayload = {
        "count": 0 if count_value is None else count_value,
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
    count_value: int | None = data_payload.get("count")
    cursor_value: str | None = data_payload.get("cursor")
    normalized_payload: TeamApiReadEventsNormalizedPayload = {
        "count": 0 if count_value is None else count_value,
        "cursor": "" if cursor_value is None else cursor_value,
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
    worker_value: str | None = data_payload.get("worker")
    count_value: int | None = data_payload.get("count")
    normalized_payload: TeamApiMailboxListNormalizedPayload = {
        "worker": "" if worker_value is None else worker_value,
        "count": 0 if count_value is None else count_value,
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


async def read_team_api_read_config_error(
    request: TeamApiReadConfigRequest,
) -> TeamApiReadConfigError:
    """Reads typed team-api config error envelopes.

    Args:
        request [TeamApiReadConfigRequest]: Typed request boundary for `omx team api read-config`.

    Returns:
        TeamApiReadConfigError: Normalized error envelope built from the nested unsuccessful `error` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-config",
            "--input",
            orjson.dumps({"team_name": request.team_name}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    normalized_payload: TeamApiErrorTransportPayload = _load_team_api_error_payload(
        stdout,
        "omx team api read-config",
    )
    result: TeamApiReadConfigError = TeamApiReadConfigError.model_validate(
        normalized_payload
    )
    return result


async def read_team_api_read_config(
    request: TeamApiReadConfigRequest,
) -> TeamApiReadConfigSnapshot:
    """Reads typed team-api config snapshots."""

    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-config",
            "--input",
            orjson.dumps({"team_name": request.team_name}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    data_payload: TeamApiTransportPayload = _load_team_api_payload(
        stdout,
        "omx team api read-config",
    )
    raw_config_payload: object = data_payload.get("config")
    if not isinstance(raw_config_payload, dict):
        raw_config_payload = None

    normalized_payload = {"config": raw_config_payload}
    result: TeamApiReadConfigSnapshot = TeamApiReadConfigSnapshot.model_validate(
        normalized_payload
    )
    return result


async def read_team_api_read_manifest_error(
    request: TeamApiReadManifestRequest,
) -> TeamApiReadManifestError:
    """Reads typed team-api manifest error envelopes.

    Args:
        request [TeamApiReadManifestRequest]: Typed request boundary for `omx team api read-manifest`.

    Returns:
        TeamApiReadManifestError: Normalized error envelope built from the nested unsuccessful `error` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-manifest",
            "--input",
            orjson.dumps({"team_name": request.team_name}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    normalized_payload: TeamApiErrorTransportPayload = _load_team_api_error_payload(
        stdout,
        "omx team api read-manifest",
    )
    result: TeamApiReadManifestError = TeamApiReadManifestError.model_validate(
        normalized_payload
    )
    return result


async def read_team_api_read_worker_status(
    request: TeamApiReadWorkerStatusRequest,
) -> TeamApiWorkerStatusSnapshot:
    """Reads typed team-api worker-status snapshots."""

    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-worker-status",
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
        "omx team api read-worker-status",
    )
    raw_status_payload: object = data_payload.get("status")
    if not isinstance(raw_status_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api read-worker-status returned a non-object status payload"
        )

    status_payload: TeamApiTransportWorkerStatusPayload = {}

    state_value: object | None = raw_status_payload.get("state")
    if isinstance(state_value, str):
        status_payload["state"] = state_value

    updated_at_value: object | None = raw_status_payload.get("updated_at")
    if isinstance(updated_at_value, str):
        status_payload["updated_at"] = updated_at_value

    worker_value: str | None = data_payload.get("worker")

    normalized_payload: TeamApiWorkerStatusNormalizedPayload = {
        "worker": "" if worker_value is None else worker_value,
        "state": "" if status_payload.get("state") is None else status_payload["state"],
        "updated_at": "" if status_payload.get("updated_at") is None else status_payload["updated_at"],
    }
    result: TeamApiWorkerStatusSnapshot = TeamApiWorkerStatusSnapshot.model_validate(
        normalized_payload
    )
    return result
