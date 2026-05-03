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
from omx_remote.schemas.runtime_schemas import (
    RuntimeModeStatusRequest,
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
)
from omx_remote.shared.exceptions.runtime_exceptions import RuntimeSurfaceError


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

    result: RuntimeModeStatusTransportPayload = {
        "statuses": parsed_payload.get("statuses"),
    }
    return result


def _normalize_runtime_mode_status_entry(
    mode_name: str,
    status_payload: object,
) -> RuntimeModeStatusSnapshot:
    """Normalizes one requested runtime mode-status entry."""
    if not isinstance(status_payload, dict):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-object mode-status payload"
        )

    normalized_transport_payload: RuntimeModeStatusEntryPayload = {
        "active": status_payload.get("active"),
        "phase": status_payload.get("phase"),
        "path": status_payload.get("path"),
        "data": status_payload.get("data"),
    }

    phase_value: object | None = normalized_transport_payload.get("phase")
    nested_data_payload: object | None = normalized_transport_payload.get("data")
    if phase_value is None and isinstance(nested_data_payload, dict):
        normalized_data_payload: RuntimeModeStatusDataPayload = {
            "current_phase": nested_data_payload.get("current_phase"),
        }
        phase_value = normalized_data_payload.get("current_phase")
    if phase_value == "":
        phase_value = None

    state_path_value: object | None = normalized_transport_payload.get("path")
    if state_path_value == "":
        state_path_value = None

    normalized_payload: RuntimeModeStatusNormalizedPayload = {
        "name": mode_name,
        "is_active": normalized_transport_payload.get("active"),
        "phase": phase_value,
        "state_path": state_path_value,
    }
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
    raw_statuses: object = parsed_payload.get("statuses")
    if not isinstance(raw_statuses, dict):
        raise RuntimeSurfaceError(
            "omx state get-status returned a non-object statuses payload"
        )

    if requested_mode not in raw_statuses:
        missing_result_payload: RuntimeModeStatusResultNormalizedPayload = {
            "requested_mode": requested_mode,
            "found": False,
            "mode_snapshot": None,
        }
        missing_result: RuntimeModeStatusResult = RuntimeModeStatusResult.model_validate(
            missing_result_payload
        )
        return missing_result

    raw_mode_payload: object = raw_statuses[requested_mode]
    mode_snapshot: RuntimeModeStatusSnapshot = _normalize_runtime_mode_status_entry(
        requested_mode,
        raw_mode_payload,
    )
    normalized_payload: RuntimeModeStatusResultNormalizedPayload = {
        "requested_mode": requested_mode,
        "found": True,
        "mode_snapshot": mode_snapshot,
    }
    result: RuntimeModeStatusResult = RuntimeModeStatusResult.model_validate(
        normalized_payload
    )
    return result
