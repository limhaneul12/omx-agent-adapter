import asyncio

import orjson

from omx_remote.adapter_types.bridge_types import (
    AdapterProbeNormalizedPayload,
    AdapterProbeRuntimePayload,
    AdapterProbeTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.bridge_schemas import AdapterProbeRequest, AdapterProbeSnapshot
from omx_remote.shared.exceptions.bridge_exceptions import BridgeSurfaceError


async def probe_adapter(request: AdapterProbeRequest) -> AdapterProbeSnapshot:
    """Reads one typed adapter probe surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> probe --json`.

    Returns:
        AdapterProbeSnapshot: Normalized probe contract built from the live adapt probe payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        ["adapt", request.target, "probe", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterProbeSnapshot = _normalize_adapter_probe(stdout)
    return result


def _load_adapter_probe_transport_payload(stdout: str) -> AdapterProbeTransportPayload:
    """Loads one adapter probe transport payload from raw stdout."""
    if not stdout:
        raise BridgeSurfaceError("omx adapt probe returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise BridgeSurfaceError("omx adapt probe returned unparseable JSON output") from error

    if not isinstance(parsed_payload, dict):
        raise BridgeSurfaceError("omx adapt probe returned a non-object JSON payload")

    result: AdapterProbeTransportPayload = {
        "target": parsed_payload.get("target"),
        "phase": parsed_payload.get("phase"),
        "summary": parsed_payload.get("summary"),
        "capabilities": parsed_payload.get("capabilities"),
        "targetRuntime": parsed_payload.get("targetRuntime"),
    }
    return result


def _normalize_adapter_probe(stdout: str) -> AdapterProbeSnapshot:
    """Normalizes one `omx adapt <target> probe --json` payload.

    Args:
        stdout [str]: Raw stdout text returned from the adapt probe command.

    Returns:
        AdapterProbeSnapshot: Validated normalized probe contract.

    Raises:
        BridgeSurfaceError: Raised when the transport is empty, not JSON, or not a JSON object.
    """
    parsed_payload: AdapterProbeTransportPayload = _load_adapter_probe_transport_payload(
        stdout
    )

    target_runtime_payload: object | None = parsed_payload.get("targetRuntime")
    target_runtime_state: str | None = None
    target_runtime_detail: str | None = None
    if isinstance(target_runtime_payload, dict):
        normalized_target_runtime_payload: AdapterProbeRuntimePayload = {
            "state": target_runtime_payload.get("state"),
            "detail": target_runtime_payload.get("detail"),
        }
        target_runtime_state = normalized_target_runtime_payload["state"]
        target_runtime_detail = normalized_target_runtime_payload["detail"]

    capabilities_payload: object | None = parsed_payload.get("capabilities")
    normalized_capabilities: object = capabilities_payload
    if capabilities_payload is None:
        normalized_capabilities = []

    normalized_payload: AdapterProbeNormalizedPayload = {
        "target": parsed_payload.get("target"),
        "phase": parsed_payload.get("phase"),
        "summary": parsed_payload.get("summary"),
        "capabilities": normalized_capabilities,
        "target_runtime_state": target_runtime_state,
        "target_runtime_detail": target_runtime_detail,
    }
    result: AdapterProbeSnapshot = AdapterProbeSnapshot.model_validate(
        normalized_payload
    )
    return result
