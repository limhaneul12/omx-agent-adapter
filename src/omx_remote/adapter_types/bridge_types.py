from typing import NotRequired, Required, TypedDict


class AdapterProbeRuntimePayload(TypedDict):
    """Represents the stable runtime subset nested under adapter probe payloads."""

    state: Required[str | None]
    detail: Required[str | None]
    evidence: NotRequired[object]


class AdapterProbeTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for adapter probe."""

    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    targetRuntime: NotRequired[AdapterProbeRuntimePayload | object]


class AdapterProbeNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for adapter probe."""

    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    target_runtime_state: Required[str | None]
    target_runtime_detail: Required[str | None]


class AdapterStatusRuntimePayload(TypedDict):
    """Represents the stable runtime subset nested under adapter status payloads."""

    state: Required[str | None]
    detail: Required[str | None]
    configPath: NotRequired[str | None]
    envelopePath: NotRequired[str | None]
    evidence: NotRequired[object]


class AdapterStatusTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for adapter status."""

    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    adapter: NotRequired[AdapterStatusRuntimePayload | object]
    targetRuntime: NotRequired[AdapterProbeRuntimePayload | object]


class AdapterStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for adapter status."""

    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    adapter_state: Required[str | None]
    adapter_detail: Required[str | None]
    target_runtime_state: Required[str | None]
    target_runtime_detail: Required[str | None]


class AdapterEnvelopeRuntimePayload(TypedDict):
    """Represents the stable runtime subset nested under adapter envelope payloads."""

    state: Required[str | None]
    detail: Required[str | None]
    evidence: NotRequired[object]


class AdapterEnvelopeTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for adapter envelope."""

    target: Required[str | None]
    displayName: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    targetRuntime: NotRequired[AdapterEnvelopeRuntimePayload | object]


class AdapterEnvelopeNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for adapter envelope."""

    target: Required[str | None]
    display_name: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    target_runtime_state: Required[str | None]
    target_runtime_detail: Required[str | None]
