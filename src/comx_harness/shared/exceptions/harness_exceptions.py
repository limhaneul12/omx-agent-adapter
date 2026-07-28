class HarnessError(RuntimeError):
    """Base error for stable harness failures."""

    code = "harness_error"


class RunNotFoundError(HarnessError):
    """Raised when a requested run record does not exist."""

    code = "run_not_found"


class UnsupportedOperationError(HarnessError):
    """Raised when a requested operation has no safe native implementation."""

    code = "unsupported_operation"


class ArtifactNotFoundError(HarnessError):
    """Raised when required verified handoff evidence is unavailable."""

    code = "artifact_not_found"
