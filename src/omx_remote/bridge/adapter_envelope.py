import orjson

from omx_remote.adapter_types.bridge_types import (
    AdapterEnvelopeNormalizedPayload,
    AdapterEnvelopeTransportPayload,
)
from omx_remote.bridge.adapter_transport_payloads import (
    load_capabilities_payload,
    load_envelope_runtime_payload,
    require_string_field,
)
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.bridge_adapter_schemas import (
    AdapterEnvelopeSnapshot,
    AdapterProbeRequest,
)
from omx_remote.shared.exceptions import BridgeSurfaceError


async def read_adapter_envelope(
    request: AdapterProbeRequest,
) -> AdapterEnvelopeSnapshot:
    """Reads one typed adapter envelope surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> envelope --json`.

    Returns:
        AdapterEnvelopeSnapshot: Normalized envelope contract built from the live adapt envelope payload.
    """
    command_result = await run_blocking_call(
        run_omx_command,
        ("adapt", request.target, "envelope", "--json"),
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterEnvelopeSnapshot = _normalize_adapter_envelope(stdout)
    return result


def _load_adapter_envelope_transport_payload(
    stdout: str,
) -> AdapterEnvelopeTransportPayload:
    """Loads one adapter envelope transport payload from raw stdout.

    Args:
        stdout [str]: Function argument.

    Returns:
        AdapterEnvelopeTransportPayload: Function return value.
    """
    if not stdout:
        raise BridgeSurfaceError("omx adapt envelope returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise BridgeSurfaceError(
            "omx adapt envelope returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise BridgeSurfaceError(
            "omx adapt envelope returned a non-object JSON payload"
        )

    result = AdapterEnvelopeTransportPayload(
        target=require_string_field(parsed_payload, "target", "omx adapt envelope"),
        displayName=require_string_field(
            parsed_payload,
            "displayName",
            "omx adapt envelope",
        ),
        summary=require_string_field(parsed_payload, "summary", "omx adapt envelope"),
        capabilities=load_capabilities_payload(
            parsed_payload.get("capabilities"),
            "omx adapt envelope",
        ),
        targetRuntime=load_envelope_runtime_payload(
            parsed_payload.get("targetRuntime"),
            "omx adapt envelope",
        ),
    )
    return result


def _normalize_adapter_envelope(stdout: str) -> AdapterEnvelopeSnapshot:
    """Normalizes one `omx adapt <target> envelope --json` payload.

    Args:
        stdout [str]: Function argument.

    Returns:
        AdapterEnvelopeSnapshot: Function return value.
    """
    parsed_payload: AdapterEnvelopeTransportPayload = (
        _load_adapter_envelope_transport_payload(stdout)
    )

    target_runtime_payload = parsed_payload["targetRuntime"]
    target_runtime_state: str = target_runtime_payload["state"]
    target_runtime_detail: str = target_runtime_payload["detail"]
    normalized_capabilities = parsed_payload["capabilities"]

    normalized_payload = AdapterEnvelopeNormalizedPayload(
        target=parsed_payload["target"],
        display_name=parsed_payload["displayName"],
        summary=parsed_payload["summary"],
        capabilities=normalized_capabilities,
        target_runtime_state=target_runtime_state,
        target_runtime_detail=target_runtime_detail,
    )
    result: AdapterEnvelopeSnapshot = AdapterEnvelopeSnapshot.model_validate(
        normalized_payload
    )
    return result
