from typing import NotRequired, TypedDict


class AdapterProbeRuntimePayload(TypedDict):
    state: object
    detail: object


class AdapterProbeTransportPayload(TypedDict):
    target: object
    phase: object
    summary: object
    capabilities: object
    targetRuntime: NotRequired[object]


class AdapterProbeNormalizedPayload(TypedDict):
    target: object
    phase: object
    summary: object
    capabilities: object
    target_runtime_state: object
    target_runtime_detail: object


class AdapterStatusRuntimePayload(TypedDict):
    state: object
    detail: object


class AdapterStatusTransportPayload(TypedDict):
    target: object
    phase: object
    summary: object
    capabilities: object
    adapter: NotRequired[object]
    targetRuntime: NotRequired[object]


class AdapterStatusNormalizedPayload(TypedDict):
    target: object
    phase: object
    summary: object
    capabilities: object
    adapter_state: object
    adapter_detail: object
    target_runtime_state: object
    target_runtime_detail: object


class AdapterEnvelopeRuntimePayload(TypedDict):
    state: object
    detail: object


class AdapterEnvelopeTransportPayload(TypedDict):
    target: object
    displayName: object
    summary: object
    capabilities: object
    targetRuntime: NotRequired[object]


class AdapterEnvelopeNormalizedPayload(TypedDict):
    target: object
    display_name: object
    summary: object
    capabilities: object
    target_runtime_state: object
    target_runtime_detail: object
