from omx_remote.adapter_types.teams_type.team_api_transport_payloads import (
    TeamApiReadConfigTransportPayload,
    TeamApiReadMonitorSnapshotTransportPayload,
    TeamApiTransportEventPayload,
    TeamApiTransportMailboxMessagePayload,
    TeamApiTransportPayload,
    TeamApiTransportTaskPayload,
    TeamApiTransportWorkerStatusPayload,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiReadConfigSnapshot,
    TeamApiReadMonitorSnapshot,
    TeamApiWorkerStatusSnapshot,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError
from omx_remote.shared.json_transport import json_object_or_none
from omx_remote.shared.utils.json_model_dump import json_value_from_object


def normalize_team_api_task_payload(
    task_payload: object,
) -> TeamApiTransportTaskPayload:
    """Normalizes one raw team-api task item into the typed subset.

    Args:
        task_payload [object]: Raw task item from `omx team api list-tasks`.

    Returns:
        TeamApiTransportTaskPayload: Stable task subset accepted by the public schema boundary.
    """
    if not isinstance(task_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api list-tasks returned a non-object task payload"
        )

    normalized_payload = TeamApiTransportTaskPayload()
    id_value: object | None = task_payload.get("id")
    subject_value: object | None = task_payload.get(
        "subject", task_payload.get("title")
    )
    status_value: object | None = task_payload.get("status")
    owner_value: object | None = task_payload.get("owner", task_payload.get("assignee"))

    if isinstance(id_value, str):
        normalized_payload["id"] = id_value
    if isinstance(subject_value, str):
        normalized_payload["subject"] = subject_value
    if isinstance(status_value, str):
        normalized_payload["status"] = status_value
    if isinstance(owner_value, str):
        normalized_payload["owner"] = owner_value

    return normalized_payload


def normalize_team_api_event_payload(
    event_payload: object,
) -> TeamApiTransportEventPayload:
    """Normalizes one raw team-api event item into the typed subset.

    Args:
        event_payload [object]: Raw event item from `omx team api read-events`.

    Returns:
        TeamApiTransportEventPayload: Stable event subset accepted by the public schema boundary.
    """
    if not isinstance(event_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api read-events returned a non-object event payload"
        )

    normalized_payload = TeamApiTransportEventPayload()
    type_value: object | None = event_payload.get("type")
    worker_value: object | None = event_payload.get("worker")
    task_id_value: object | None = event_payload.get("task_id")
    message_id_value: object | None = event_payload.get("message_id")

    if isinstance(type_value, str):
        normalized_payload["type"] = type_value
    if isinstance(worker_value, str):
        normalized_payload["worker"] = worker_value
    if isinstance(task_id_value, str):
        normalized_payload["task_id"] = task_id_value
    if message_id_value is None or isinstance(message_id_value, str):
        normalized_payload["message_id"] = message_id_value

    return normalized_payload


def normalize_team_api_mailbox_message_payload(
    message_payload: object,
) -> TeamApiTransportMailboxMessagePayload:
    """Normalizes one raw team-api mailbox message into the typed subset.

    Args:
        message_payload [object]: Raw mailbox item from `omx team api mailbox-list`.

    Returns:
        TeamApiTransportMailboxMessagePayload: Stable message subset accepted by the public schema boundary.
    """
    if not isinstance(message_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api mailbox-list returned a non-object message payload"
        )

    normalized_payload = TeamApiTransportMailboxMessagePayload()
    id_value: object | None = message_payload.get("id")
    subject_value: object | None = message_payload.get("subject")
    body_value: object | None = message_payload.get("body")
    delivered_value: object | None = message_payload.get("delivered")

    if isinstance(id_value, str):
        normalized_payload["id"] = id_value
    if isinstance(subject_value, str):
        normalized_payload["subject"] = subject_value
    if isinstance(body_value, str):
        normalized_payload["body"] = body_value
    if isinstance(delivered_value, bool):
        normalized_payload["delivered"] = delivered_value

    return normalized_payload


def normalize_team_api_worker_status_payload(
    worker_name: object,
    status_payload: object,
) -> TeamApiWorkerStatusSnapshot:
    """Normalizes one raw team-api worker-status payload into the typed subset.

    Args:
        worker_name [object]: Worker name from the enclosing team-api data payload.
        status_payload [object]: Raw status object from `omx team api read-worker-status`.

    Returns:
        TeamApiWorkerStatusSnapshot: Stable worker-status snapshot accepted by the schema boundary.
    """
    if not isinstance(status_payload, dict):
        raise TeamworkSurfaceError(
            "omx team api read-worker-status returned a non-object status payload"
        )

    normalized_status_payload = TeamApiTransportWorkerStatusPayload()
    state_value: object | None = status_payload.get("state")
    updated_at_value: object | None = status_payload.get("updated_at")

    if isinstance(state_value, str):
        normalized_status_payload["state"] = state_value
    if isinstance(updated_at_value, str):
        normalized_status_payload["updated_at"] = updated_at_value

    normalized_worker = _required_string_value(
        value=worker_name,
        context="omx team api read-worker-status worker",
    )
    normalized_state = _required_string_value(
        value=normalized_status_payload.get("state"),
        context="omx team api read-worker-status state",
    )
    normalized_updated_at = _required_string_value(
        value=normalized_status_payload.get("updated_at"),
        context="omx team api read-worker-status updated_at",
    )
    result = TeamApiWorkerStatusSnapshot(
        worker=normalized_worker,
        state=normalized_state,
        updated_at=normalized_updated_at,
    )
    return result


def normalize_team_api_monitor_snapshot_result(
    data_payload: TeamApiReadMonitorSnapshotTransportPayload | TeamApiTransportPayload,
) -> TeamApiReadMonitorSnapshot:
    """Normalizes one team-api monitor snapshot result from loaded data.

    Args:
        data_payload [TeamApiTransportPayload]: Stable team-api data subset.

    Returns:
        TeamApiReadMonitorSnapshot: Typed monitor snapshot result.
    """
    snapshot_value: object = data_payload.get("snapshot")
    snapshot_json = (
        None
        if snapshot_value is None
        else json_value_from_object(
            snapshot_value,
            context="omx team api read-monitor-snapshot snapshot",
        )
    )
    result = TeamApiReadMonitorSnapshot(snapshot=snapshot_json)
    return result


def normalize_team_api_config_snapshot_result(
    data_payload: TeamApiReadConfigTransportPayload | TeamApiTransportPayload,
) -> TeamApiReadConfigSnapshot:
    """Normalizes one team-api config snapshot result from loaded data.

    Args:
        data_payload [TeamApiTransportPayload]: Stable team-api data subset.

    Returns:
        TeamApiReadConfigSnapshot: Typed config snapshot result.
    """
    raw_config_payload: object = data_payload.get("config")
    config_payload = json_object_or_none(raw_config_payload)

    result = TeamApiReadConfigSnapshot(config=config_payload)
    return result


def _required_string_value(value: object, context: str) -> str:
    """Return a required string value or raise a Teamwork boundary error.

    Args:
        value [object]: Candidate value from a Team API payload.
        context [str]: Human-readable field context.

    Returns:
        str: Validated string value.
    """
    if not isinstance(value, str):
        raise TeamworkSurfaceError(f"{context} must be a string")
    return value
