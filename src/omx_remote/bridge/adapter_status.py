import asyncio

import orjson

from omx_remote.adapter_types.bridge_types import (
    AdapterStatusNormalizedPayload,
    AdapterStatusRuntimePayload,
    AdapterStatusTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.bridge_schemas import AdapterProbeRequest, AdapterStatusSnapshot
from omx_remote.shared.exceptions.bridge_exceptions import BridgeSurfaceError


async def read_adapter_status(request: AdapterProbeRequest) -> AdapterStatusSnapshot:
    """Reads one typed adapter status surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> status --json`.

    Returns:
        AdapterStatusSnapshot: Normalized status contract built from the live adapt status payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        ["adapt", request.target, "status", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterStatusSnapshot = _normalize_adapter_status(stdout)
    return result


def _load_adapter_status_transport_payload(stdout: str) -> AdapterStatusTransportPayload:
    """Loads one adapter status transport payload from raw stdout."""
    if not stdout:
        raise BridgeSurfaceError("omx adapt status returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise BridgeSurfaceError(
            "omx adapt status returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise BridgeSurfaceError("omx adapt status returned a non-object JSON payload")

    result: AdapterStatusTransportPayload = {
        "target": parsed_payload.get("target"),
        "phase": parsed_payload.get("phase"),
        "summary": parsed_payload.get("summary"),
        "capabilities": parsed_payload.get("capabilities"),
        "adapter": parsed_payload.get("adapter"),
        "targetRuntime": parsed_payload.get("targetRuntime"),
    }
    return result


def _normalize_adapter_status(stdout: str) -> AdapterStatusSnapshot:
    """Normalizes one `omx adapt <target> status --json` payload."""
    parsed_payload: AdapterStatusTransportPayload = _load_adapter_status_transport_payload(
        stdout
    )

    adapter_payload: object | None = parsed_payload.get("adapter")
    adapter_state: object | None = None
    adapter_detail: object | None = None
    if isinstance(adapter_payload, dict):
        normalized_adapter_payload: AdapterStatusRuntimePayload = {
            "state": adapter_payload.get("state"),
            "detail": adapter_payload.get("detail"),
        }
        adapter_state = normalized_adapter_payload.get("state")
        adapter_detail = normalized_adapter_payload.get("detail")

    target_runtime_payload: object | None = parsed_payload.get("targetRuntime")
    target_runtime_state: object | None = None
    target_runtime_detail: object | None = None
    if isinstance(target_runtime_payload, dict):
        normalized_target_runtime_payload: AdapterStatusRuntimePayload = {
            "state": target_runtime_payload.get("state"),
            "detail": target_runtime_payload.get("detail"),
        }
        target_runtime_state = normalized_target_runtime_payload.get("state")
        target_runtime_detail = normalized_target_runtime_payload.get("detail")

    capabilities_payload: object | None = parsed_payload.get("capabilities")
    normalized_capabilities: object = capabilities_payload
    if capabilities_payload is None:
        normalized_capabilities = []

    normalized_payload: AdapterStatusNormalizedPayload = {
        "target": parsed_payload.get("target"),
        "phase": parsed_payload.get("phase"),
        "summary": parsed_payload.get("summary"),
        "adapter_state": adapter_state,
        "adapter_detail": adapter_detail,
        "target_runtime_state": target_runtime_state,
        "target_runtime_detail": target_runtime_detail,
        "capabilities": normalized_capabilities,
    }
    result: AdapterStatusSnapshot = AdapterStatusSnapshot.model_validate(
        normalized_payload
    )
    return result
