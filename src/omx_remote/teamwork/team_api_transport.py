import msgspec
import orjson

from omx_remote.adapter_types.teamwork_types import (
    TeamApiDataSpec,
    TeamApiEnvelopePayload,
    TeamApiEnvelopeSpec,
    TeamApiErrorSpec,
    TeamApiErrorTransportPayload,
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


def _normalize_team_api_data_payload(
    data_payload: dict[str, object],
) -> TeamApiTransportPayload:
    """Normalizes one decoded team-api data object into the stable adapter subset.

    Args:
        data_payload [dict[str, object]]: Nested successful `data` payload from a team-api envelope.

    Returns:
        TeamApiTransportPayload: Stable subset shared by typed team-api readers.
    """
    data_spec: TeamApiDataSpec = msgspec.convert(
        data_payload,
        TeamApiDataSpec,
        strict=False,
    )
    result = TeamApiTransportPayload()

    if isinstance(data_spec.count, int):
        result["count"] = data_spec.count
    if isinstance(data_spec.cursor, str):
        result["cursor"] = data_spec.cursor
    if isinstance(data_spec.worker, str):
        result["worker"] = data_spec.worker

    result["tasks"] = data_spec.tasks
    result["events"] = data_spec.events
    result["messages"] = data_spec.messages
    result["snapshot"] = data_spec.snapshot
    result["status"] = data_spec.status
    result["config"] = data_spec.config
    result["manifest"] = data_spec.manifest
    return result


def load_team_api_payload(stdout: str, operation_name: str) -> TeamApiTransportPayload:
    """Loads one successful team-api nested data payload.

    Args:
        stdout [str]: Raw stdout text returned from one `omx team api ... --json` command.
        operation_name [str]: Human-readable team-api operation name used in error messages.

    Returns:
        TeamApiTransportPayload: Nested `data` object normalized into the stable adapter subset.

    Raises:
        TeamworkSurfaceError: Raised when the envelope is unsuccessful or omits a nested data object.
    """
    envelope: TeamApiEnvelopeSpec = _decode_team_api_envelope(stdout, operation_name)
    if envelope.ok is not True:
        raise TeamworkSurfaceError(f"{operation_name} returned an unsuccessful payload")

    top_level_payload = TeamApiEnvelopePayload(ok=True, data=envelope.data)
    data_payload: object = top_level_payload["data"]
    if not isinstance(data_payload, dict):
        raise TeamworkSurfaceError(
            f"{operation_name} returned a non-object data payload"
        )

    result: TeamApiTransportPayload = _normalize_team_api_data_payload(data_payload)
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
