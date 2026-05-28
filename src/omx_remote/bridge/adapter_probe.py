import orjson

from omx_remote.adapter_types.bridge_types import (
    AdapterProbeNormalizedPayload,
    AdapterProbeTransportPayload,
)
from omx_remote.bridge.adapter_transport_payloads import (
    load_capabilities_payload,
    load_probe_runtime_payload,
    require_string_field,
)
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.bridge.adapter_schemas import (
    AdapterProbeRequest,
    AdapterProbeSnapshot,
)
from omx_remote.shared.exceptions import BridgeSurfaceError


async def probe_adapter(request: AdapterProbeRequest) -> AdapterProbeSnapshot:
    """Reads one typed adapter probe surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> probe --json`.

    Returns:
        AdapterProbeSnapshot: Normalized probe contract built from the live adapt probe payload.
    """
    command_result = await run_blocking_call(
        run_omx_command,
        ["adapt", request.target, "probe", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterProbeSnapshot = _normalize_adapter_probe(stdout)
    return result


def _load_adapter_probe_transport_payload(stdout: str) -> AdapterProbeTransportPayload:
    """Loads one adapter probe transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        AdapterProbeTransportPayload: Function return value.
    """
    if not stdout:
        raise BridgeSurfaceError("omx adapt probe returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise BridgeSurfaceError("omx adapt probe returned unparseable JSON output") from error

    if not isinstance(parsed_payload, dict):
        raise BridgeSurfaceError("omx adapt probe returned a non-object JSON payload")

    result = AdapterProbeTransportPayload(
        target=require_string_field(parsed_payload, "target", "omx adapt probe"),
        phase=require_string_field(parsed_payload, "phase", "omx adapt probe"),
        summary=require_string_field(parsed_payload, "summary", "omx adapt probe"),
        capabilities=load_capabilities_payload(
            parsed_payload.get("capabilities"),
            "omx adapt probe",
        ),
        targetRuntime=load_probe_runtime_payload(
            parsed_payload.get("targetRuntime"),
            "omx adapt probe",
        ),
    )
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

    target_runtime_payload = parsed_payload["targetRuntime"]
    target_runtime_state: str = target_runtime_payload["state"]
    target_runtime_detail: str = target_runtime_payload["detail"]
    normalized_capabilities = parsed_payload["capabilities"]

    normalized_payload = AdapterProbeNormalizedPayload(
        target=parsed_payload["target"],
        phase=parsed_payload["phase"],
        summary=parsed_payload["summary"],
        capabilities=normalized_capabilities,
        target_runtime_state=target_runtime_state,
        target_runtime_detail=target_runtime_detail,
    )
    result: AdapterProbeSnapshot = AdapterProbeSnapshot.model_validate(
        normalized_payload
    )
    return result
