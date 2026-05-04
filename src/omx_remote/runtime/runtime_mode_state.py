import asyncio

import orjson

from omx_remote.adapter_types.runtime_types import RuntimeModeStateTransportPayload
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.runtime_schemas import (
    RuntimeModeStateRequest,
    RuntimeModeStateResult,
)
from omx_remote.shared.exceptions.runtime_exceptions import RuntimeSurfaceError


async def read_runtime_mode_state(
    request: RuntimeModeStateRequest,
) -> RuntimeModeStateResult:
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
    return _normalize_runtime_mode_state(stdout=stdout)


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

    return {
        "exists": parsed_payload.get("exists", True),
        "mode": parsed_payload.get("mode"),
        "state": parsed_payload.get("state", parsed_payload),
    }


def _normalize_runtime_mode_state(*, stdout: str) -> RuntimeModeStateResult:
    """Normalizes `omx state read --json` stdout into a stable contract."""
    parsed_payload: RuntimeModeStateTransportPayload = _load_runtime_mode_state_payload(
        stdout
    )
    raw_state: object | None = parsed_payload.get("state")
    exists_value: object | None = parsed_payload.get("exists")
    if exists_value is False:
        return RuntimeModeStateResult.model_validate(
            {
                "mode": parsed_payload.get("mode"),
                "exists": False,
                "state": None,
            }
        )

    if not isinstance(raw_state, dict):
        raise RuntimeSurfaceError("omx state read returned a non-object state payload")

    return RuntimeModeStateResult.model_validate(
        {
            "mode": parsed_payload.get("mode"),
            "exists": True,
            "state": raw_state,
        }
    )
