from typing import NotRequired

from typing_extensions import TypedDict


class AdapterRuntimeEvidencePayload(TypedDict, extra_items=object):
    """Represents target-owned runtime evidence with target-specific keys."""


class AdapterCapabilityTransportPayload(TypedDict, closed=True):
    """Represents one stable capability item emitted by adapter bridge payloads."""

    id: str
    label: str
    ownership: str
    status: str
    summary: str


class AdapterProbeRuntimePayload(TypedDict, closed=True):
    """Represents the stable runtime subset nested under adapter probe payloads."""

    state: str
    detail: str
    evidence: NotRequired[AdapterRuntimeEvidencePayload]


class AdapterProbeTransportPayload(TypedDict, closed=True):
    """Represents the stable top-level transport subset for adapter probe."""

    target: str
    phase: str
    summary: str
    capabilities: list[AdapterCapabilityTransportPayload]
    targetRuntime: AdapterProbeRuntimePayload


class AdapterProbeNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for adapter probe."""

    target: str
    phase: str
    summary: str
    capabilities: list[AdapterCapabilityTransportPayload]
    target_runtime_state: str
    target_runtime_detail: str


class AdapterStatusRuntimePayload(TypedDict, closed=True):
    """Represents the stable runtime subset nested under adapter status payloads."""

    state: str
    detail: str
    configPath: NotRequired[str]
    envelopePath: NotRequired[str]
    evidence: NotRequired[AdapterRuntimeEvidencePayload]


class AdapterStatusTransportPayload(TypedDict, closed=True):
    """Represents the stable top-level transport subset for adapter status."""

    target: str
    phase: str
    summary: str
    capabilities: list[AdapterCapabilityTransportPayload]
    adapter: AdapterStatusRuntimePayload
    targetRuntime: AdapterProbeRuntimePayload


class AdapterStatusNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for adapter status."""

    target: str
    phase: str
    summary: str
    capabilities: list[AdapterCapabilityTransportPayload]
    adapter_state: str
    adapter_detail: str
    target_runtime_state: str
    target_runtime_detail: str


class AdapterEnvelopeRuntimePayload(TypedDict, closed=True):
    """Represents the stable runtime subset nested under adapter envelope payloads."""

    state: str
    detail: str
    evidence: NotRequired[AdapterRuntimeEvidencePayload]


class AdapterEnvelopeTransportPayload(TypedDict, closed=True):
    """Represents the stable top-level transport subset for adapter envelope."""

    target: str
    displayName: str
    summary: str
    capabilities: list[AdapterCapabilityTransportPayload]
    targetRuntime: AdapterEnvelopeRuntimePayload


class AdapterEnvelopeNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for adapter envelope."""

    target: str
    display_name: str
    summary: str
    capabilities: list[AdapterCapabilityTransportPayload]
    target_runtime_state: str
    target_runtime_detail: str
