from enum import StrEnum


class RuntimeMode(StrEnum):
    """Top-level OMX runtime domains exposed through adapter status surfaces."""

    EXECUTION = "execution"
    TEAMWORK = "teamwork"
    HISTORY = "history"
    BRIDGE = "bridge"


class RuntimeModeStatus(StrEnum):
    """Normalized activity status for one OMX runtime mode."""

    ACTIVE = "active"
    PAUSED = "paused"
    IDLE = "idle"
    UNKNOWN = "unknown"


class RuntimeStatusAnomalyCategory(StrEnum):
    """Categories for runtime status transport and normalization anomalies."""

    STDERR_FALLBACK = "stderr_fallback"
    UNKNOWN_MODE_STATUS = "unknown_mode_status"
    EMPTY_TRANSPORT_OUTPUT = "empty_transport_output"
    UNPARSEABLE_STDOUT = "unparseable_stdout"
