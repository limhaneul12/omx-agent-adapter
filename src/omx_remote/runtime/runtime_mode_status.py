import asyncio

import orjson

from omx_remote.adapter_types.runtime_types import (
    RuntimeModeStatusDataPayload,
    RuntimeModeStatusEntryPayload,
    RuntimeModeStatusNormalizedPayload,
    RuntimeModeStatusResultNormalizedPayload,
    RuntimeModeStatusTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.runtime import (
    RuntimeModeStatusRequest,
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
)
from omx_remote.shared.exceptions import RuntimeSurfaceError


async def read_runtime_mode_status(
    request: RuntimeModeStatusRequest,
) -> RuntimeModeStatusResult:
    """Reads and normalizes one OMX runtime mode-status snapshot."""

    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "state",
            "get-status",
            "--input",
            orjson.dumps({"mode": request.mode}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    result: RuntimeModeStatusResult = _normalize_runtime_mode_status(
        stdout=stdout,
        requested_mode=request.mode,
    )
    return result


def _load_runtime_mode_status_payload(stdout: str) -> RuntimeModeStatusTransportPayload:
    """Loads one runtime mode-status transport payload from raw stdout."""
    if not stdout:
        raise RuntimeSurfaceError("omx state get-status returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise RuntimeSurfaceError(
            "omx state get-status returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-object JSON payload"
        )

    statuses_payload: object | None = parsed_payload.get("statuses")
    if not isinstance(statuses_payload, dict):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-object statuses payload"
        )

    normalized_statuses: dict[str, RuntimeModeStatusEntryPayload] = {}
    raw_mode_name: object
    raw_status_payload: object
    for raw_mode_name, raw_status_payload in statuses_payload.items():
        if not isinstance(raw_mode_name, str):
            raise RuntimeSurfaceError(
                "omx state get-status returned a non-string status key"
            )
        normalized_statuses[raw_mode_name] = _normalize_runtime_mode_status_entry_payload(
            raw_status_payload
        )

    result = RuntimeModeStatusTransportPayload(
        statuses=normalized_statuses,
    )
    return result


def _normalize_runtime_mode_status_data_payload(
    nested_data_payload: object,
) -> RuntimeModeStatusDataPayload:
    """Normalize one nested runtime mode-status data payload into the stable subset."""
    if not isinstance(nested_data_payload, dict):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-object nested data payload"
        )

    current_phase_value: object | None = nested_data_payload.get("current_phase")
    normalized_data_payload: RuntimeModeStatusDataPayload = {}
    if isinstance(current_phase_value, str):
        normalized_data_payload["current_phase"] = current_phase_value

    return normalized_data_payload


def _normalize_runtime_mode_status_entry_payload(
    status_payload: object,
) -> RuntimeModeStatusEntryPayload:
    """Normalize one raw runtime mode-status entry transport payload."""
    if not isinstance(status_payload, dict):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-object mode-status payload"
        )

    active_value: object | None = status_payload.get("active")
    if not isinstance(active_value, bool):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-boolean active payload"
        )

    normalized_transport_payload = RuntimeModeStatusEntryPayload(
        active=active_value,
    )

    phase_value: object | None = status_payload.get("phase")
    if phase_value is None or isinstance(phase_value, str):
        normalized_transport_payload["phase"] = phase_value

    path_value: object | None = status_payload.get("path")
    if path_value is None or isinstance(path_value, str):
        normalized_transport_payload["path"] = path_value

    data_value: object | None = status_payload.get("data")
    if data_value is None:
        normalized_transport_payload["data"] = None
    elif isinstance(data_value, dict):
        normalized_transport_payload["data"] = _normalize_runtime_mode_status_data_payload(
            data_value
        )

    return normalized_transport_payload


def _normalize_runtime_mode_status_entry(
    mode_name: str,
    status_payload: RuntimeModeStatusEntryPayload,
) -> RuntimeModeStatusSnapshot:
    """Normalizes one requested runtime mode-status entry."""
    phase_value: str | None = status_payload.get("phase")
    if phase_value == "":
        phase_value = None

    nested_data_payload: RuntimeModeStatusDataPayload | None = status_payload.get("data")
    if phase_value is None and isinstance(nested_data_payload, dict):
        phase_value = nested_data_payload.get("current_phase")

    state_path_value: str | None = status_payload.get("path")
    if state_path_value == "":
        state_path_value = None

    normalized_payload = RuntimeModeStatusNormalizedPayload(
        name=mode_name,
        is_active=status_payload["active"],
        phase=phase_value,
        state_path=state_path_value,
    )
    result: RuntimeModeStatusSnapshot = RuntimeModeStatusSnapshot.model_validate(
        normalized_payload
    )
    return result


def _normalize_runtime_mode_status(
    *,
    stdout: str,
    requested_mode: str,
) -> RuntimeModeStatusResult:
    """Normalizes `omx state get-status --json` stdout into a stable contract."""
    parsed_payload: RuntimeModeStatusTransportPayload = _load_runtime_mode_status_payload(
        stdout
    )
    raw_statuses: dict[str, RuntimeModeStatusEntryPayload] = parsed_payload["statuses"]

    if requested_mode not in raw_statuses:
        missing_result_payload = RuntimeModeStatusResultNormalizedPayload(
            requested_mode=requested_mode,
            found=False,
            mode_snapshot=None,
        )
        missing_result: RuntimeModeStatusResult = RuntimeModeStatusResult.model_validate(
            missing_result_payload
        )
        return missing_result

    raw_mode_payload: RuntimeModeStatusEntryPayload = raw_statuses[requested_mode]
    mode_snapshot: RuntimeModeStatusSnapshot = _normalize_runtime_mode_status_entry(
        requested_mode,
        raw_mode_payload,
    )
    normalized_payload = RuntimeModeStatusResultNormalizedPayload(
        requested_mode=requested_mode,
        found=True,
        mode_snapshot=RuntimeModeStatusNormalizedPayload(
            name=mode_snapshot.name,
            is_active=mode_snapshot.is_active,
            phase=mode_snapshot.phase,
            state_path=mode_snapshot.state_path,
        ),
    )
    result: RuntimeModeStatusResult = RuntimeModeStatusResult.model_validate(
        normalized_payload
    )
    return result
