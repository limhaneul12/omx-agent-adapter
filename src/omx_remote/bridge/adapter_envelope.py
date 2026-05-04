import asyncio

import orjson

from omx_remote.adapter_types.bridge_types import (
    AdapterEnvelopeNormalizedPayload,
    AdapterEnvelopeRuntimePayload,
    AdapterEnvelopeTransportPayload,
)
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.bridge_schemas import (
    AdapterEnvelopeSnapshot,
    AdapterProbeRequest,
)
from omx_remote.shared.exceptions import BridgeSurfaceError


async def read_adapter_envelope(request: AdapterProbeRequest) -> AdapterEnvelopeSnapshot:
    """Reads one typed adapter envelope surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> envelope --json`.

    Returns:
        AdapterEnvelopeSnapshot: Normalized envelope contract built from the live adapt envelope payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        ["adapt", request.target, "envelope", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterEnvelopeSnapshot = _normalize_adapter_envelope(stdout)
    return result


def _load_adapter_envelope_transport_payload(stdout: str) -> AdapterEnvelopeTransportPayload:
    """Loads one adapter envelope transport payload from raw stdout."""
    if not stdout:
        raise BridgeSurfaceError("omx adapt envelope returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise BridgeSurfaceError(
            "omx adapt envelope returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise BridgeSurfaceError("omx adapt envelope returned a non-object JSON payload")

    result = AdapterEnvelopeTransportPayload(
        target=parsed_payload.get("target"),
        displayName=parsed_payload.get("displayName"),
        summary=parsed_payload.get("summary"),
        capabilities=parsed_payload.get("capabilities"),
        targetRuntime=parsed_payload.get("targetRuntime"),
    )
    return result


def _normalize_adapter_envelope(stdout: str) -> AdapterEnvelopeSnapshot:
    """Normalizes one `omx adapt <target> envelope --json` payload."""
    parsed_payload: AdapterEnvelopeTransportPayload = _load_adapter_envelope_transport_payload(
        stdout
    )

    target_runtime_payload: object | None = parsed_payload.get("targetRuntime")
    target_runtime_state: str | None = None
    target_runtime_detail: str | None = None
    if isinstance(target_runtime_payload, dict):
        normalized_target_runtime_payload = AdapterEnvelopeRuntimePayload(
            state=target_runtime_payload.get("state"),
            detail=target_runtime_payload.get("detail"),
        )
        target_runtime_state = normalized_target_runtime_payload["state"]
        target_runtime_detail = normalized_target_runtime_payload["detail"]

    capabilities_payload: object | None = parsed_payload.get("capabilities")
    normalized_capabilities: object = capabilities_payload
    if capabilities_payload is None:
        normalized_capabilities = []

    normalized_payload = AdapterEnvelopeNormalizedPayload(
        target=parsed_payload.get("target"),
        display_name=parsed_payload.get("displayName"),
        summary=parsed_payload.get("summary"),
        capabilities=normalized_capabilities,
        target_runtime_state=target_runtime_state,
        target_runtime_detail=target_runtime_detail,
    )
    result: AdapterEnvelopeSnapshot = AdapterEnvelopeSnapshot.model_validate(
        normalized_payload
    )
    return result
