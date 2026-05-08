import asyncio
from typing import cast

import orjson

from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.adapter_types.runtime_types import (
    RuntimeModeStateDataPayload,
    RuntimeModeStateNormalizedPayload,
    RuntimeModeStateTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStateSnapshot,
)
from omx_remote.shared.exceptions import RuntimeSurfaceError


async def read_runtime_mode_state(
    request: RuntimeModeStateRequest,
) -> RuntimeModeStateSnapshot:
    """Reads and normalizes one OMX runtime mode-state snapshot.
    
    Args:
        request [RuntimeModeStateRequest]: Function argument.
    
    Returns:
        RuntimeModeStateSnapshot: Function return value.
    """

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
    """Loads one runtime mode-state transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        RuntimeModeStateTransportPayload: Function return value.
    """
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

    mode_value: object | None = parsed_payload.get("mode")
    if not isinstance(mode_value, str):
        raise RuntimeSurfaceError("omx state read returned a non-string mode payload")

    exists_value: object | None = parsed_payload.get("exists")
    if exists_value is None:
        direct_state_payload: RuntimeModeStateDataPayload = (
            _copy_runtime_mode_state_payload(parsed_payload)
        )
        direct_result = RuntimeModeStateTransportPayload(
            exists=True,
            mode=mode_value,
            state=direct_state_payload,
        )
        return direct_result

    if not isinstance(exists_value, bool):
        raise RuntimeSurfaceError("omx state read returned a non-boolean exists payload")

    state_value: object | None = parsed_payload.get("state")
    if state_value is not None and not isinstance(state_value, dict):
        raise RuntimeSurfaceError("omx state read returned a non-object state payload")

    normalized_state_value: RuntimeModeStateDataPayload | None = None
    if isinstance(state_value, dict):
        normalized_state_value = _copy_runtime_mode_state_payload(state_value)

    result = RuntimeModeStateTransportPayload(
        exists=exists_value,
        mode=mode_value,
        state=normalized_state_value,
    )

    return result


def _copy_runtime_mode_state_payload(
    payload: dict[object, object],
) -> RuntimeModeStateDataPayload:
    """Copies a runtime mode-state object into a string-keyed payload.

    Args:
        payload [dict[object, object]]: Runtime mode-state object decoded from OMX JSON.

    Returns:
        RuntimeModeStateDataPayload: Stable string-keyed state payload for schema validation.
    """
    copied_payload = RuntimeModeStateDataPayload()
    for key, value in payload.items():
        if not isinstance(key, str):
            raise RuntimeSurfaceError("omx state read returned a non-string state key")
        copied_payload[key] = cast(JsonValue, value)

    return copied_payload


def _normalize_runtime_mode_state(stdout: str) -> RuntimeModeStateSnapshot:
    """Normalizes `omx state read --json` stdout into a stable contract.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        RuntimeModeStateSnapshot: Function return value.
    """
    payload: RuntimeModeStateTransportPayload = _load_runtime_mode_state_payload(stdout)
    raw_state_payload: RuntimeModeStateDataPayload | None = payload.get("state")

    normalized_payload = RuntimeModeStateNormalizedPayload(
        mode=payload["mode"],
        exists=payload["exists"],
        state=raw_state_payload,
    )
    result: RuntimeModeStateSnapshot = RuntimeModeStateSnapshot.model_validate(
        normalized_payload
    )
    return result
