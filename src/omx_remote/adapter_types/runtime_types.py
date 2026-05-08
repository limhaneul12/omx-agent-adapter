from typing import NotRequired

from typing_extensions import TypedDict

from omx_remote.adapter_types.json_types import JsonValue


class RuntimeModeStateDataPayload(TypedDict, extra_items=JsonValue):
    """Represents a mode-owned runtime state mapping with string keys."""

    # Mode state values stay JSON-shaped because each OMX runtime mode owns its payload shape.


class RuntimeModeStatusDataPayload(TypedDict, total=False, closed=True):
    """Represents the stable nested transport subset for runtime mode-status data."""

    current_phase: str


class RuntimeModeStatusEntryPayload(TypedDict, closed=True):
    """Represents one stable transport entry from `omx state get-status`."""

    active: bool
    phase: NotRequired[str | None]
    path: NotRequired[str | None]
    data: NotRequired[RuntimeModeStatusDataPayload | None]


class RuntimeModeStatusTransportPayload(TypedDict, closed=True):
    """Represents the stable top-level transport subset for runtime mode status."""

    statuses: dict[str, RuntimeModeStatusEntryPayload]


class ActiveRuntimeModesTransportPayload(TypedDict, closed=True):
    """Represents the stable transport subset for active runtime modes."""

    active_modes: list[str]


class RuntimeModeStateTransportPayload(TypedDict, closed=True):
    """Represents the stable transport subset for runtime mode state reads."""

    exists: bool
    mode: str
    state: NotRequired[RuntimeModeStateDataPayload | None]


class RuntimeModeStateNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for runtime mode state."""

    mode: str
    exists: bool
    state: RuntimeModeStateDataPayload | None


class RuntimeModeStatusNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for one runtime mode snapshot."""

    name: str
    is_active: bool
    phase: str | None
    state_path: str | None


class RuntimeModeStatusResultNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for one status lookup result."""

    requested_mode: str
    found: bool
    mode_snapshot: RuntimeModeStatusNormalizedPayload | None
