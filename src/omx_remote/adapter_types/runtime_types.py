from typing import NotRequired, Required, TypedDict


class RuntimeModeStatusDataPayload(TypedDict, total=False):
    current_phase: str


class RuntimeModeStatusEntryPayload(TypedDict):
    active: Required[bool]
    phase: NotRequired[str | None]
    path: NotRequired[str | None]
    data: NotRequired[RuntimeModeStatusDataPayload | None]


class RuntimeModeStatusTransportPayload(TypedDict):
    statuses: Required[dict[str, RuntimeModeStatusEntryPayload]]


class ActiveRuntimeModesTransportPayload(TypedDict):
    active_modes: Required[list[str]]


class RuntimeModeStateTransportPayload(TypedDict):
    exists: Required[bool]
    mode: Required[str]
    state: NotRequired[dict[str, object] | None]


class RuntimeModeStateNormalizedPayload(TypedDict):
    mode: Required[str]
    exists: Required[bool]
    state: Required[dict[str, object] | None]


class RuntimeModeStatusNormalizedPayload(TypedDict):
    name: Required[str]
    is_active: Required[bool]
    phase: Required[str | None]
    state_path: Required[str | None]


class RuntimeModeStatusResultNormalizedPayload(TypedDict):
    requested_mode: Required[str]
    found: Required[bool]
    mode_snapshot: Required[RuntimeModeStatusNormalizedPayload | None]
