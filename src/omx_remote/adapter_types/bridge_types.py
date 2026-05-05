from typing import NotRequired, TypedDict


class AdapterProbeRuntimePayload(TypedDict):
    """Represents the stable runtime subset nested under adapter probe payloads."""

    state: str | None
    detail: str | None
    evidence: NotRequired[object]


class AdapterProbeTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for adapter probe."""

    target: str | None
    phase: str | None
    summary: str | None
    capabilities: object
    targetRuntime: NotRequired[AdapterProbeRuntimePayload | object]


class AdapterProbeNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for adapter probe."""

    target: str | None
    phase: str | None
    summary: str | None
    capabilities: object
    target_runtime_state: str | None
    target_runtime_detail: str | None


class AdapterStatusRuntimePayload(TypedDict):
    """Represents the stable runtime subset nested under adapter status payloads."""

    state: str | None
    detail: str | None
    configPath: NotRequired[str | None]
    envelopePath: NotRequired[str | None]
    evidence: NotRequired[object]


class AdapterStatusTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for adapter status."""

    target: str | None
    phase: str | None
    summary: str | None
    capabilities: object
    adapter: NotRequired[AdapterStatusRuntimePayload | object]
    targetRuntime: NotRequired[AdapterProbeRuntimePayload | object]


class AdapterStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for adapter status."""

    target: str | None
    phase: str | None
    summary: str | None
    capabilities: object
    adapter_state: str | None
    adapter_detail: str | None
    target_runtime_state: str | None
    target_runtime_detail: str | None


class AdapterEnvelopeRuntimePayload(TypedDict):
    """Represents the stable runtime subset nested under adapter envelope payloads."""

    state: str | None
    detail: str | None
    evidence: NotRequired[object]


class AdapterEnvelopeTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for adapter envelope."""

    target: str | None
    displayName: str | None
    summary: str | None
    capabilities: object
    targetRuntime: NotRequired[AdapterEnvelopeRuntimePayload | object]


class AdapterEnvelopeNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for adapter envelope."""

    target: str | None
    display_name: str | None
    summary: str | None
    capabilities: object
    target_runtime_state: str | None
    target_runtime_detail: str | None
