import asyncio

import orjson

from omx_remote.adapter_types.teams_type.team_api_raw_payloads import (
    TeamApiRawEventPayload,
    TeamApiRawMailboxMessagePayload,
    TeamApiRawTaskPayload,
)
from omx_remote.adapter_types.teams_type.team_api_transport_payloads import (
    TeamApiErrorTransportPayload,
    TeamApiListTasksNormalizedPayload,
    TeamApiListTasksTransportPayload,
    TeamApiMailboxListNormalizedPayload,
    TeamApiMailboxListTransportPayload,
    TeamApiReadConfigTransportPayload,
    TeamApiReadEventsNormalizedPayload,
    TeamApiReadEventsTransportPayload,
    TeamApiReadMonitorSnapshotTransportPayload,
    TeamApiReadWorkerStatusTransportPayload,
    TeamApiTransportEventPayload,
    TeamApiTransportMailboxMessagePayload,
    TeamApiTransportTaskPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiListTasksRequest,
    TeamApiMailboxListRequest,
    TeamApiReadConfigRequest,
    TeamApiReadEventsRequest,
    TeamApiReadManifestRequest,
    TeamApiReadMonitorSnapshotRequest,
    TeamApiReadWorkerStatusRequest,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiListTasksSnapshot,
    TeamApiMailboxListSnapshot,
    TeamApiReadConfigError,
    TeamApiReadConfigSnapshot,
    TeamApiReadEventsSnapshot,
    TeamApiReadManifestError,
    TeamApiReadMonitorSnapshot,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.teamwork.team_api_normalizers import (
    normalize_team_api_config_snapshot_result,
    normalize_team_api_event_payload,
    normalize_team_api_mailbox_message_payload,
    normalize_team_api_monitor_snapshot_result,
    normalize_team_api_task_payload,
    normalize_team_api_worker_status_payload,
)
from omx_remote.teamwork.team_api_transport import (
    load_team_api_error_payload,
    load_team_api_list_tasks_payload,
    load_team_api_mailbox_list_payload,
    load_team_api_read_config_payload,
    load_team_api_read_events_payload,
    load_team_api_read_monitor_snapshot_payload,
    load_team_api_read_worker_status_payload,
)


def _validate_count_matches_length(
    operation_name: str,
    count_value: int,
    actual_length: int,
    collection_name: str,
) -> None:
    """Validates that a transport count matches the normalized collection length.

    Args:
        operation_name [str]: Team-api operation name used in error messages.
        count_value [int]: Count reported by the team-api transport payload.
        actual_length [int]: Actual normalized collection length.
        collection_name [str]: Human-readable collection name used in error messages.
    """
    if count_value != actual_length:
        raise TeamworkSurfaceError(
            f"{operation_name} returned count that does not match {collection_name} length"
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
    data_payload: TeamApiListTasksTransportPayload = load_team_api_list_tasks_payload(
        command_result.stdout.strip()
    )
    raw_tasks: list[TeamApiRawTaskPayload] = data_payload["tasks"]
    count_value: int = data_payload["count"]
    normalized_tasks: list[TeamApiTransportTaskPayload] = [
        normalize_team_api_task_payload(task_payload) for task_payload in raw_tasks
    ]
    normalized_payload = TeamApiListTasksNormalizedPayload(
        count=count_value,
        tasks=normalized_tasks,
    )
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
    data_payload: TeamApiReadEventsTransportPayload = load_team_api_read_events_payload(
        command_result.stdout.strip()
    )
    raw_events: list[TeamApiRawEventPayload] = data_payload["events"]
    count_value: int = data_payload["count"]
    cursor_value: str = data_payload["cursor"]
    normalized_events: list[TeamApiTransportEventPayload] = [
        normalize_team_api_event_payload(event_payload) for event_payload in raw_events
    ]
    normalized_payload = TeamApiReadEventsNormalizedPayload(
        count=count_value,
        cursor=cursor_value,
        events=normalized_events,
    )
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
            orjson.dumps({"team_name": request.team_name, "worker": request.worker}).decode(),
            "--json",
        ],
    )
    data_payload: TeamApiMailboxListTransportPayload = load_team_api_mailbox_list_payload(
        command_result.stdout.strip()
    )
    raw_messages: list[TeamApiRawMailboxMessagePayload] = data_payload["messages"]
    worker_value: str = data_payload["worker"]
    count_value: int = data_payload["count"]
    normalized_messages: list[TeamApiTransportMailboxMessagePayload] = [
        normalize_team_api_mailbox_message_payload(message_payload)
        for message_payload in raw_messages
    ]
    normalized_payload = TeamApiMailboxListNormalizedPayload(
        worker=worker_value,
        count=count_value,
        messages=normalized_messages,
    )
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
    data_payload: TeamApiReadMonitorSnapshotTransportPayload = (
        load_team_api_read_monitor_snapshot_payload(command_result.stdout.strip())
    )
    result: TeamApiReadMonitorSnapshot = normalize_team_api_monitor_snapshot_result(
        data_payload
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
    normalized_payload: TeamApiErrorTransportPayload = load_team_api_error_payload(
        command_result.stdout.strip(),
        "omx team api read-config",
    )
    result: TeamApiReadConfigError = TeamApiReadConfigError.model_validate(
        normalized_payload
    )
    return result


async def read_team_api_read_config(
    request: TeamApiReadConfigRequest,
) -> TeamApiReadConfigSnapshot:
    """Reads typed team-api config snapshots.

    Args:
        request [TeamApiReadConfigRequest]: Typed request boundary for `omx team api read-config`.

    Returns:
        TeamApiReadConfigSnapshot: Normalized config snapshot built from the nested successful `data` payload.
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
    data_payload: TeamApiReadConfigTransportPayload = load_team_api_read_config_payload(
        command_result.stdout.strip()
    )
    result: TeamApiReadConfigSnapshot = normalize_team_api_config_snapshot_result(
        data_payload
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
    normalized_payload: TeamApiErrorTransportPayload = load_team_api_error_payload(
        command_result.stdout.strip(),
        "omx team api read-manifest",
    )
    result: TeamApiReadManifestError = TeamApiReadManifestError.model_validate(
        normalized_payload
    )
    return result


async def read_team_api_read_worker_status(
    request: TeamApiReadWorkerStatusRequest,
) -> TeamApiWorkerStatusSnapshot:
    """Reads typed team-api worker-status snapshots.

    Args:
        request [TeamApiReadWorkerStatusRequest]: Typed request boundary for `omx team api read-worker-status`.

    Returns:
        TeamApiWorkerStatusSnapshot: Normalized worker-status snapshot built from the nested successful `data` payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "team",
            "api",
            "read-worker-status",
            "--input",
            orjson.dumps({"team_name": request.team_name, "worker": request.worker}).decode(),
            "--json",
        ],
    )
    data_payload: TeamApiReadWorkerStatusTransportPayload = (
        load_team_api_read_worker_status_payload(command_result.stdout.strip())
    )
    result: TeamApiWorkerStatusSnapshot = normalize_team_api_worker_status_payload(
        data_payload["worker"],
        data_payload["status"],
    )
    return result
