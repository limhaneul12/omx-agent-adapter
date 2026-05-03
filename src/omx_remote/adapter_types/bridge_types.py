from typing import NotRequired, Required, TypedDict


class AdapterProbeRuntimePayload(TypedDict):
    state: Required[object]
    detail: Required[object]


class AdapterProbeTransportPayload(TypedDict):
    target: Required[object]
    phase: Required[object]
    summary: Required[object]
    capabilities: Required[object]
    targetRuntime: NotRequired[object]


class AdapterProbeNormalizedPayload(TypedDict):
    target: Required[object]
    phase: Required[object]
    summary: Required[object]
    capabilities: Required[object]
    target_runtime_state: Required[object]
    target_runtime_detail: Required[object]


class AdapterStatusRuntimePayload(TypedDict):
    state: Required[object]
    detail: Required[object]


class AdapterStatusTransportPayload(TypedDict):
    target: Required[object]
    phase: Required[object]
    summary: Required[object]
    capabilities: Required[object]
    adapter: NotRequired[object]
    targetRuntime: NotRequired[object]


class AdapterStatusNormalizedPayload(TypedDict):
    target: Required[object]
    phase: Required[object]
    summary: Required[object]
    capabilities: Required[object]
    adapter_state: Required[object]
    adapter_detail: Required[object]
    target_runtime_state: Required[object]
    target_runtime_detail: Required[object]


class AdapterEnvelopeRuntimePayload(TypedDict):
    state: Required[object]
    detail: Required[object]


class AdapterEnvelopeTransportPayload(TypedDict):
    target: Required[object]
    displayName: Required[object]
    summary: Required[object]
    capabilities: Required[object]
    targetRuntime: NotRequired[object]


class AdapterEnvelopeNormalizedPayload(TypedDict):
    target: Required[object]
    display_name: Required[object]
    summary: Required[object]
    capabilities: Required[object]
    target_runtime_state: Required[object]
    target_runtime_detail: Required[object]
