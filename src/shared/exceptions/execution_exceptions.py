class ExecutionError(Exception):
    """Raised when OMX execution handling fails."""


class UnsupportedExecutionPayloadError(ExecutionError):
    """Raised when an execution payload cannot be promoted into a supported contract."""
