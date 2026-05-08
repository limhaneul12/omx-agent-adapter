import asyncio

import orjson

from omx_remote.adapter_types.bridge_types import (
    AdapterStatusNormalizedPayload,
    AdapterStatusTransportPayload,
)
from omx_remote.bridge.adapter_transport_payloads import (
    load_capabilities_payload,
    load_probe_runtime_payload,
    load_status_runtime_payload,
    require_string_field,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.bridge.adapter_schemas import (
    AdapterProbeRequest,
    AdapterStatusSnapshot,
)
from omx_remote.shared.exceptions import BridgeSurfaceError


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
    """Loads one adapter status transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        AdapterStatusTransportPayload: Function return value.
    """
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

    result = AdapterStatusTransportPayload(
        target=require_string_field(parsed_payload, "target", "omx adapt status"),
        phase=require_string_field(parsed_payload, "phase", "omx adapt status"),
        summary=require_string_field(parsed_payload, "summary", "omx adapt status"),
        capabilities=load_capabilities_payload(
            parsed_payload.get("capabilities"),
            "omx adapt status",
        ),
        adapter=load_status_runtime_payload(
            parsed_payload.get("adapter"),
            "omx adapt status adapter",
        ),
        targetRuntime=load_probe_runtime_payload(
            parsed_payload.get("targetRuntime"),
            "omx adapt status targetRuntime",
        ),
    )
    return result


def _normalize_adapter_status(stdout: str) -> AdapterStatusSnapshot:
    """Normalizes one `omx adapt <target> status --json` payload.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        AdapterStatusSnapshot: Function return value.
    """
    parsed_payload: AdapterStatusTransportPayload = _load_adapter_status_transport_payload(
        stdout
    )

    adapter_payload = parsed_payload["adapter"]
    adapter_state: str = adapter_payload["state"]
    adapter_detail: str = adapter_payload["detail"]

    target_runtime_payload = parsed_payload["targetRuntime"]
    target_runtime_state: str = target_runtime_payload["state"]
    target_runtime_detail: str = target_runtime_payload["detail"]
    normalized_capabilities = parsed_payload["capabilities"]

    normalized_payload = AdapterStatusNormalizedPayload(
        target=parsed_payload["target"],
        phase=parsed_payload["phase"],
        summary=parsed_payload["summary"],
        adapter_state=adapter_state,
        adapter_detail=adapter_detail,
        target_runtime_state=target_runtime_state,
        target_runtime_detail=target_runtime_detail,
        capabilities=normalized_capabilities,
    )
    result: AdapterStatusSnapshot = AdapterStatusSnapshot.model_validate(
        normalized_payload
    )
    return result
