from typing import NotRequired, TypedDict


class RuntimeModeStatusDataPayload(TypedDict, total=False):
    """Represents the stable nested transport subset for runtime mode-status data."""

    current_phase: str


class RuntimeModeStatusEntryPayload(TypedDict):
    """Represents one stable transport entry from `omx state get-status`."""

    active: bool
    phase: NotRequired[str | None]
    path: NotRequired[str | None]
    data: NotRequired[RuntimeModeStatusDataPayload | None]


class RuntimeModeStatusTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for runtime mode status."""

    statuses: dict[str, RuntimeModeStatusEntryPayload]


class ActiveRuntimeModesTransportPayload(TypedDict):
    """Represents the stable transport subset for active runtime modes."""

    active_modes: list[str]


class RuntimeModeStateTransportPayload(TypedDict):
    """Represents the stable transport subset for runtime mode state reads."""

    exists: bool
    mode: str
    state: NotRequired[dict[str, object] | None]


class RuntimeModeStateNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for runtime mode state."""

    mode: str
    exists: bool
    state: dict[str, object] | None


class RuntimeModeStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for one runtime mode snapshot."""

    name: str
    is_active: bool
    phase: str | None
    state_path: str | None


class RuntimeModeStatusResultNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for one status lookup result."""

    requested_mode: str
    found: bool
    mode_snapshot: RuntimeModeStatusNormalizedPayload | None
