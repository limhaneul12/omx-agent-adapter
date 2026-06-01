from omx_remote.schemas.runtime_status_schemas import RuntimeModeStatus

IDLE_RUNTIME_SUMMARY = "No active modes."
ACTIVE_MODE_MARKER = RuntimeModeStatus.ACTIVE
KNOWN_MODE_STATUS_MARKERS: tuple[RuntimeModeStatus, ...] = (
    RuntimeModeStatus.ACTIVE,
    RuntimeModeStatus.PAUSED,
    RuntimeModeStatus.IDLE,
    RuntimeModeStatus.UNKNOWN,
)
RUNTIME_STATUS_PREFIXES: tuple[tuple[str, RuntimeModeStatus], ...] = (
    ("active", RuntimeModeStatus.ACTIVE),
    ("paused", RuntimeModeStatus.PAUSED),
    ("idle", RuntimeModeStatus.IDLE),
    ("inactive", RuntimeModeStatus.IDLE),
)
