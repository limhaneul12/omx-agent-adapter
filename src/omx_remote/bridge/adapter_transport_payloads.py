from omx_remote.adapter_types.bridge_types import (
    AdapterCapabilityTransportPayload,
    AdapterEnvelopeRuntimePayload,
    AdapterProbeRuntimePayload,
    AdapterRuntimeEvidencePayload,
    AdapterStatusRuntimePayload,
)
from omx_remote.shared.exceptions import BridgeSurfaceError


def require_string_field(
    payload: dict[object, object],
    key: str,
    source: str,
) -> str:
    """Reads one required string field from a decoded adapter transport object.

    Args:
        payload [dict[object, object]]: Decoded JSON object containing the requested field.
        key [str]: Field name to read.
        source [str]: Human-readable source label for error messages.

    Returns:
        str: Required string field value.
    """
    value: object | None = payload.get(key)
    if not isinstance(value, str):
        raise BridgeSurfaceError(f"{source} returned a non-string {key} payload")

    result: str = value
    return result


def load_capabilities_payload(
    raw_capabilities_payload: object,
    source: str,
) -> list[AdapterCapabilityTransportPayload]:
    """Loads the stable capability subset from a decoded adapter transport object.

    Args:
        raw_capabilities_payload [object]: Raw decoded `capabilities` value.
        source [str]: Human-readable source label for error messages.

    Returns:
        list[AdapterCapabilityTransportPayload]: Stable capability payloads.
    """
    if not isinstance(raw_capabilities_payload, list):
        raise BridgeSurfaceError(f"{source} returned a non-list capabilities payload")

    capabilities: list[AdapterCapabilityTransportPayload] = []
    raw_capability_payload: object
    for raw_capability_payload in raw_capabilities_payload:
        if not isinstance(raw_capability_payload, dict):
            raise BridgeSurfaceError(
                f"{source} returned a non-object capability payload"
            )
        capability_payload = AdapterCapabilityTransportPayload(
            id=require_string_field(raw_capability_payload, "id", source),
            label=require_string_field(raw_capability_payload, "label", source),
            status=require_string_field(raw_capability_payload, "status", source),
            summary=require_string_field(raw_capability_payload, "summary", source),
        )
        ownership_value: object | None = raw_capability_payload.get("ownership")
        if ownership_value is not None:
            if not isinstance(ownership_value, str):
                raise BridgeSurfaceError(
                    f"{source} returned a non-string ownership payload"
                )
            capability_payload["ownership"] = ownership_value
        capabilities.append(capability_payload)

    result: list[AdapterCapabilityTransportPayload] = capabilities
    return result


def load_probe_runtime_payload(
    raw_runtime_payload: object,
    source: str,
) -> AdapterProbeRuntimePayload:
    """Loads the stable target-runtime subset from an adapter probe payload.

    Args:
        raw_runtime_payload [object]: Raw decoded `targetRuntime` value.
        source [str]: Human-readable source label for error messages.

    Returns:
        AdapterProbeRuntimePayload: Stable target-runtime payload.
    """
    if not isinstance(raw_runtime_payload, dict):
        raise BridgeSurfaceError(f"{source} returned a non-object targetRuntime payload")

    runtime_payload = AdapterProbeRuntimePayload(
        state=require_string_field(raw_runtime_payload, "state", source),
        detail=require_string_field(raw_runtime_payload, "detail", source),
    )
    if "evidence" in raw_runtime_payload:
        runtime_payload["evidence"] = copy_runtime_evidence_payload(
            raw_runtime_payload["evidence"],
            source,
        )

    result: AdapterProbeRuntimePayload = runtime_payload
    return result


def load_status_runtime_payload(
    raw_runtime_payload: object,
    source: str,
) -> AdapterStatusRuntimePayload:
    """Loads the stable adapter/target runtime subset from an adapter status payload.

    Args:
        raw_runtime_payload [object]: Raw decoded adapter or target runtime value.
        source [str]: Human-readable source label for error messages.

    Returns:
        AdapterStatusRuntimePayload: Stable runtime payload.
    """
    if not isinstance(raw_runtime_payload, dict):
        raise BridgeSurfaceError(f"{source} returned a non-object runtime payload")

    runtime_payload = AdapterStatusRuntimePayload(
        state=require_string_field(raw_runtime_payload, "state", source),
        detail=require_string_field(raw_runtime_payload, "detail", source),
    )
    config_path_value: object | None = raw_runtime_payload.get("configPath")
    if config_path_value is not None:
        if not isinstance(config_path_value, str):
            raise BridgeSurfaceError(
                f"{source} returned a non-string configPath payload"
            )
        runtime_payload["configPath"] = config_path_value

    envelope_path_value: object | None = raw_runtime_payload.get("envelopePath")
    if envelope_path_value is not None:
        if not isinstance(envelope_path_value, str):
            raise BridgeSurfaceError(
                f"{source} returned a non-string envelopePath payload"
            )
        runtime_payload["envelopePath"] = envelope_path_value

    if "evidence" in raw_runtime_payload:
        runtime_payload["evidence"] = copy_runtime_evidence_payload(
            raw_runtime_payload["evidence"],
            source,
        )

    result: AdapterStatusRuntimePayload = runtime_payload
    return result


def load_envelope_runtime_payload(
    raw_runtime_payload: object,
    source: str,
) -> AdapterEnvelopeRuntimePayload:
    """Loads the stable target-runtime subset from an adapter envelope payload.

    Args:
        raw_runtime_payload [object]: Raw decoded `targetRuntime` value.
        source [str]: Human-readable source label for error messages.

    Returns:
        AdapterEnvelopeRuntimePayload: Stable target-runtime payload.
    """
    if not isinstance(raw_runtime_payload, dict):
        raise BridgeSurfaceError(f"{source} returned a non-object targetRuntime payload")

    runtime_payload = AdapterEnvelopeRuntimePayload(
        state=require_string_field(raw_runtime_payload, "state", source),
        detail=require_string_field(raw_runtime_payload, "detail", source),
    )
    if "evidence" in raw_runtime_payload:
        runtime_payload["evidence"] = copy_runtime_evidence_payload(
            raw_runtime_payload["evidence"],
            source,
        )

    result: AdapterEnvelopeRuntimePayload = runtime_payload
    return result


def copy_runtime_evidence_payload(
    raw_evidence_payload: object,
    source: str,
) -> AdapterRuntimeEvidencePayload:
    """Copies target-owned runtime evidence while requiring string keys.

    Args:
        raw_evidence_payload [object]: Raw decoded `evidence` value.
        source [str]: Human-readable source label for error messages.

    Returns:
        AdapterRuntimeEvidencePayload: String-keyed runtime evidence payload.
    """
    if not isinstance(raw_evidence_payload, dict):
        raise BridgeSurfaceError(f"{source} returned a non-object evidence payload")

    evidence_payload = AdapterRuntimeEvidencePayload()
    raw_key: object
    raw_value: object
    for raw_key, raw_value in raw_evidence_payload.items():
        if not isinstance(raw_key, str):
            raise BridgeSurfaceError(f"{source} returned a non-string evidence key")
        evidence_payload[raw_key] = raw_value

    result: AdapterRuntimeEvidencePayload = evidence_payload
    return result
