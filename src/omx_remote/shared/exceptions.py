class BridgeSurfaceError(Exception):
    """Raised when adapt/bridge surface inspection fails."""


class ExecutionError(Exception):
    """Raised when OMX execution handling fails."""


class UnsupportedExecutionPayloadError(ExecutionError):
    """Raised when an execution payload cannot be promoted into a supported contract."""


class HistorySurfaceError(Exception):
    """Raised when history/session surface inspection fails."""


class RuntimeSurfaceError(Exception):
    """Raised when runtime surface inspection fails."""


class TeamworkSurfaceError(Exception):
    """Raised when teamwork surface inspection fails."""
