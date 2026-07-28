from comx_harness.shared.exceptions.harness_exceptions import HarnessError


class IdempotencyConflictError(HarnessError):
    """Raised when an idempotency key is reused with a different request."""

    code = "idempotency_conflict"


class IdempotencyLockTimeoutError(HarnessError):
    """Raised when an idempotency claim cannot acquire its local lock."""

    code = "idempotency_lock_timeout"
