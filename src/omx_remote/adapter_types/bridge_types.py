from typing import NotRequired, Required, TypedDict


class AdapterProbeRuntimePayload(TypedDict):
    state: Required[str | None]
    detail: Required[str | None]
    evidence: NotRequired[object]


class AdapterProbeTransportPayload(TypedDict):
    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    targetRuntime: NotRequired[AdapterProbeRuntimePayload | object]


class AdapterProbeNormalizedPayload(TypedDict):
    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    target_runtime_state: Required[str | None]
    target_runtime_detail: Required[str | None]


class AdapterStatusRuntimePayload(TypedDict):
    state: Required[str | None]
    detail: Required[str | None]
    configPath: NotRequired[str | None]
    envelopePath: NotRequired[str | None]
    evidence: NotRequired[object]


class AdapterStatusTransportPayload(TypedDict):
    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    adapter: NotRequired[AdapterStatusRuntimePayload | object]
    targetRuntime: NotRequired[AdapterProbeRuntimePayload | object]


class AdapterStatusNormalizedPayload(TypedDict):
    target: Required[str | None]
    phase: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    adapter_state: Required[str | None]
    adapter_detail: Required[str | None]
    target_runtime_state: Required[str | None]
    target_runtime_detail: Required[str | None]


class AdapterEnvelopeRuntimePayload(TypedDict):
    state: Required[str | None]
    detail: Required[str | None]
    evidence: NotRequired[object]


class AdapterEnvelopeTransportPayload(TypedDict):
    target: Required[str | None]
    displayName: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    targetRuntime: NotRequired[AdapterEnvelopeRuntimePayload | object]


class AdapterEnvelopeNormalizedPayload(TypedDict):
    target: Required[str | None]
    display_name: Required[str | None]
    summary: Required[str | None]
    capabilities: Required[object]
    target_runtime_state: Required[str | None]
    target_runtime_detail: Required[str | None]
