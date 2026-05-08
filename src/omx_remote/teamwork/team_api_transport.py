import msgspec
import orjson

from omx_remote.adapter_types.teamwork_types import (
    TeamApiEnvelopePayload,
    TeamApiEnvelopeSpec,
    TeamApiErrorSpec,
    TeamApiErrorTransportPayload,
    TeamApiListTasksDataSpec,
    TeamApiListTasksTransportPayload,
    TeamApiMailboxListDataSpec,
    TeamApiMailboxListTransportPayload,
    TeamApiReadConfigDataSpec,
    TeamApiReadConfigTransportPayload,
    TeamApiReadEventsDataSpec,
    TeamApiReadEventsTransportPayload,
    TeamApiReadMonitorSnapshotDataSpec,
    TeamApiReadMonitorSnapshotTransportPayload,
    TeamApiReadWorkerStatusDataSpec,
    TeamApiReadWorkerStatusTransportPayload,
    TeamApiTransportPayload,
)
from omx_remote.shared.exceptions import TeamworkSurfaceError


def _decode_team_api_envelope(stdout: str, operation_name: str) -> TeamApiEnvelopeSpec:
    """Decodes one team-api JSON envelope with msgspec.

    Args:
        stdout [str]: Raw stdout text emitted by `omx team api ... --json`.
        operation_name [str]: Human-readable operation name used in error messages.

    Returns:
        TeamApiEnvelopeSpec: Decoded top-level team-api envelope.

    Raises:
        TeamworkSurfaceError: Raised when stdout is empty, invalid JSON, or not a JSON object matching the envelope shape.
    """
    if not stdout:
        raise TeamworkSurfaceError(f"{operation_name} returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
        envelope: TeamApiEnvelopeSpec = msgspec.convert(
            parsed_payload,
            TeamApiEnvelopeSpec,
            strict=False,
        )
    except (orjson.JSONDecodeError, msgspec.ValidationError) as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned unparseable JSON output"
        ) from error

    return envelope


def _load_team_api_data_object(stdout: str, operation_name: str) -> dict[str, object]:
    """Loads the successful nested data object from one team-api envelope.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        dict[str, object]: Nested successful `data` object.

    Raises:
        TeamworkSurfaceError: Raised when the envelope is unsuccessful or omits a nested data object.
    """
    envelope: TeamApiEnvelopeSpec = _decode_team_api_envelope(stdout, operation_name)
    if envelope.ok is not True:
        raise TeamworkSurfaceError(f"{operation_name} returned an unsuccessful payload")

    data_payload: object = envelope.data
    if not isinstance(data_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object data payload"
        )

    top_level_payload = TeamApiEnvelopePayload(ok=True, data=data_payload)
    result: dict[str, object] = top_level_payload["data"]
    return result


def load_team_api_list_tasks_payload(stdout: str) -> TeamApiListTasksTransportPayload:
    """Loads one list-tasks data payload with an operation-specific msgspec contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx team api list-tasks --json`.

    Returns:
        TeamApiListTasksTransportPayload: Loaded list-tasks data payload.

    Raises:
        TeamworkSurfaceError: Raised when the nested data payload is malformed.
    """
    operation_name = "omx team api list-tasks"
    data_payload: dict[str, object] = _load_team_api_data_object(stdout, operation_name)
    try:
        data_spec: TeamApiListTasksDataSpec = msgspec.convert(
            data_payload,
            TeamApiListTasksDataSpec,
            strict=True,
        )
    except msgspec.ValidationError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed data payload"
        ) from error

    result = TeamApiListTasksTransportPayload(
        count=data_spec.count,
        tasks=data_spec.tasks,
    )
    return result


def load_team_api_read_events_payload(stdout: str) -> TeamApiReadEventsTransportPayload:
    """Loads one read-events data payload with an operation-specific msgspec contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx team api read-events --json`.

    Returns:
        TeamApiReadEventsTransportPayload: Loaded read-events data payload.

    Raises:
        TeamworkSurfaceError: Raised when the nested data payload is malformed.
    """
    operation_name = "omx team api read-events"
    data_payload: dict[str, object] = _load_team_api_data_object(stdout, operation_name)
    try:
        data_spec: TeamApiReadEventsDataSpec = msgspec.convert(
            data_payload,
            TeamApiReadEventsDataSpec,
            strict=True,
        )
    except msgspec.ValidationError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed data payload"
        ) from error

    result = TeamApiReadEventsTransportPayload(
        count=data_spec.count,
        cursor=data_spec.cursor,
        events=data_spec.events,
    )
    return result


def load_team_api_mailbox_list_payload(stdout: str) -> TeamApiMailboxListTransportPayload:
    """Loads one mailbox-list data payload with an operation-specific msgspec contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx team api mailbox-list --json`.

    Returns:
        TeamApiMailboxListTransportPayload: Loaded mailbox-list data payload.

    Raises:
        TeamworkSurfaceError: Raised when the nested data payload is malformed.
    """
    operation_name = "omx team api mailbox-list"
    data_payload: dict[str, object] = _load_team_api_data_object(stdout, operation_name)
    try:
        data_spec: TeamApiMailboxListDataSpec = msgspec.convert(
            data_payload,
            TeamApiMailboxListDataSpec,
            strict=True,
        )
    except msgspec.ValidationError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed data payload"
        ) from error

    result = TeamApiMailboxListTransportPayload(
        worker=data_spec.worker,
        count=data_spec.count,
        messages=data_spec.messages,
    )
    return result


def load_team_api_read_monitor_snapshot_payload(
    stdout: str,
) -> TeamApiReadMonitorSnapshotTransportPayload:
    """Loads one monitor-snapshot data payload with an operation-specific msgspec contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx team api read-monitor-snapshot --json`.

    Returns:
        TeamApiReadMonitorSnapshotTransportPayload: Loaded monitor-snapshot data payload.

    Raises:
        TeamworkSurfaceError: Raised when the nested data payload is malformed.
    """
    operation_name = "omx team api read-monitor-snapshot"
    data_payload: dict[str, object] = _load_team_api_data_object(stdout, operation_name)
    try:
        data_spec: TeamApiReadMonitorSnapshotDataSpec = msgspec.convert(
            data_payload,
            TeamApiReadMonitorSnapshotDataSpec,
            strict=True,
        )
    except msgspec.ValidationError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed data payload"
        ) from error

    result = TeamApiReadMonitorSnapshotTransportPayload(snapshot=data_spec.snapshot)
    return result


def load_team_api_read_config_payload(stdout: str) -> TeamApiReadConfigTransportPayload:
    """Loads one read-config data payload with an operation-specific msgspec contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx team api read-config --json`.

    Returns:
        TeamApiReadConfigTransportPayload: Loaded config data payload.

    Raises:
        TeamworkSurfaceError: Raised when the nested data payload is malformed.
    """
    operation_name = "omx team api read-config"
    data_payload: dict[str, object] = _load_team_api_data_object(stdout, operation_name)
    try:
        data_spec: TeamApiReadConfigDataSpec = msgspec.convert(
            data_payload,
            TeamApiReadConfigDataSpec,
            strict=True,
        )
    except msgspec.ValidationError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed data payload"
        ) from error

    result = TeamApiReadConfigTransportPayload(config=data_spec.config)
    return result


def load_team_api_read_worker_status_payload(
    stdout: str,
) -> TeamApiReadWorkerStatusTransportPayload:
    """Loads one read-worker-status data payload with an operation-specific msgspec contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx team api read-worker-status --json`.

    Returns:
        TeamApiReadWorkerStatusTransportPayload: Loaded worker-status data payload.

    Raises:
        TeamworkSurfaceError: Raised when the nested data payload is malformed.
    """
    operation_name = "omx team api read-worker-status"
    data_payload: dict[str, object] = _load_team_api_data_object(stdout, operation_name)
    try:
        data_spec: TeamApiReadWorkerStatusDataSpec = msgspec.convert(
            data_payload,
            TeamApiReadWorkerStatusDataSpec,
            strict=True,
        )
    except msgspec.ValidationError as error:
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed data payload"
        ) from error

    result = TeamApiReadWorkerStatusTransportPayload(
        worker=data_spec.worker,
        status=data_spec.status,
    )
    return result


def load_team_api_payload(stdout: str, operation_name: str) -> TeamApiTransportPayload:
    """Loads one successful team-api nested data object for legacy generic callers.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        TeamApiTransportPayload: Empty generic transport subset after envelope/data validation.

    Raises:
        TeamworkSurfaceError: Raised when the envelope is unsuccessful or omits a nested data object.
    """
    _load_team_api_data_object(stdout, operation_name)
    result = TeamApiTransportPayload()
    return result


def load_team_api_error_payload(
    stdout: str,
    operation_name: str,
) -> TeamApiErrorTransportPayload:
    """Loads one unsuccessful team-api nested error payload.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        TeamApiErrorTransportPayload: Narrow error payload containing stable `code` and `message` fields.

    Raises:
        TeamworkSurfaceError: Raised when the envelope is successful or omits a typed nested error object.
    """
    envelope: TeamApiEnvelopeSpec = _decode_team_api_envelope(stdout, operation_name)
    if envelope.ok is not False:
        raise TeamworkSurfaceError(f"{operation_name} returned a successful payload")

    error_payload: object = envelope.error
    if not isinstance(error_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object error payload"
        )

    error_spec: TeamApiErrorSpec = msgspec.convert(
        error_payload,
        TeamApiErrorSpec,
        strict=False,
    )
    if not isinstance(error_spec.code, str) or not isinstance(error_spec.message, str):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a malformed error payload"
        )

    result = TeamApiErrorTransportPayload(
        code=error_spec.code,
        message=error_spec.message,
    )
    return result
