import asyncio

import orjson

from omx_remote.adapter_types.runtime_types import (
    RuntimeModeStateNormalizedPayload,
    RuntimeModeStateTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.runtime_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStateSnapshot,
)
from omx_remote.shared.exceptions.runtime_exceptions import RuntimeSurfaceError


async def read_runtime_mode_state(
    request: RuntimeModeStateRequest,
) -> RuntimeModeStateSnapshot:
    """Reads and normalizes one OMX runtime mode-state snapshot."""

    command_result = await asyncio.to_thread(
        run_omx_command,
        [
            "state",
            "read",
            "--input",
            orjson.dumps({"mode": request.mode}).decode(),
            "--json",
        ],
    )
    stdout: str = command_result.stdout.strip()
    result: RuntimeModeStateSnapshot = _normalize_runtime_mode_state(stdout)
    return result


def _load_runtime_mode_state_payload(stdout: str) -> RuntimeModeStateTransportPayload:
    """Loads one runtime mode-state transport payload from raw stdout."""
    if not stdout:
        raise RuntimeSurfaceError("omx state read returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise RuntimeSurfaceError(
            "omx state read returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise RuntimeSurfaceError("omx state read returned a non-object JSON payload")

    result: RuntimeModeStateTransportPayload = {
        "exists": parsed_payload.get("exists"),
        "mode": parsed_payload.get("mode"),
        "state": parsed_payload.get("state"),
    }
    return result


def _normalize_runtime_mode_state(stdout: str) -> RuntimeModeStateSnapshot:
    """Normalizes `omx state read --json` stdout into a stable contract."""
    payload: RuntimeModeStateTransportPayload = _load_runtime_mode_state_payload(stdout)
    raw_state_payload: object | None = payload.get("state")
    if raw_state_payload is not None and not isinstance(raw_state_payload, dict):
        raise RuntimeSurfaceError("omx state read returned a non-object state payload")

    normalized_payload: RuntimeModeStateNormalizedPayload = {
        "mode": payload.get("mode"),
        "exists": payload.get("exists"),
        "state": raw_state_payload,
    }
    result: RuntimeModeStateSnapshot = RuntimeModeStateSnapshot.model_validate(
        normalized_payload
    )
    return result
