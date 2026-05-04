from typing import NotRequired, Required, TypedDict


class ActiveRuntimeModesTransportPayload(TypedDict):
    active_modes: Required[object]


class RuntimeModeStateTransportPayload(TypedDict):
    exists: Required[object]
    mode: Required[object]
    state: NotRequired[object]


class RuntimeModeStateNormalizedPayload(TypedDict):
    mode: Required[object]
    exists: Required[object]
    state: Required[object]


class RuntimeModeStatusTransportPayload(TypedDict):
    statuses: Required[object]


class RuntimeModeStatusEntryPayload(TypedDict):
    active: Required[object]
    phase: NotRequired[object]
    path: NotRequired[object]
    data: NotRequired[object]


class RuntimeModeStatusDataPayload(TypedDict, total=False):
    current_phase: object


class RuntimeModeStatusNormalizedPayload(TypedDict):
    name: Required[object]
    is_active: Required[object]
    phase: Required[object]
    state_path: Required[object]


class RuntimeModeStatusResultNormalizedPayload(TypedDict):
    requested_mode: Required[object]
    found: Required[object]
    mode_snapshot: Required[object]


class RuntimeModeStateTransportPayload(TypedDict):
    exists: Required[object]
    mode: Required[object]
    state: NotRequired[object]
