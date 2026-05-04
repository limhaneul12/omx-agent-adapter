from typing import NotRequired, Required, TypedDict


class RuntimeModeStatusDataPayload(TypedDict, total=False):
    """Represents the stable nested transport subset for runtime mode-status data."""

    current_phase: NotRequired[str]


class RuntimeModeStatusEntryPayload(TypedDict):
    """Represents one stable transport entry from `omx state get-status`."""

    active: Required[bool]
    phase: NotRequired[str | None]
    path: NotRequired[str | None]
    data: NotRequired[RuntimeModeStatusDataPayload | None]


class RuntimeModeStatusTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for runtime mode status."""

    statuses: Required[dict[str, RuntimeModeStatusEntryPayload]]


class ActiveRuntimeModesTransportPayload(TypedDict):
    """Represents the stable transport subset for active runtime modes."""

    active_modes: Required[list[str]]


class RuntimeModeStateTransportPayload(TypedDict):
    """Represents the stable transport subset for runtime mode state reads."""

    exists: Required[bool]
    mode: Required[str]
    state: NotRequired[dict[str, object] | None]


class RuntimeModeStateNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for runtime mode state."""

    mode: Required[str]
    exists: Required[bool]
    state: Required[dict[str, object] | None]


class RuntimeModeStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for one runtime mode snapshot."""

    name: Required[str]
    is_active: Required[bool]
    phase: Required[str | None]
    state_path: Required[str | None]


class RuntimeModeStatusResultNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for one status lookup result."""

    requested_mode: Required[str]
    found: Required[bool]
    mode_snapshot: Required[RuntimeModeStatusNormalizedPayload | None]
