from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.invoke_command_schemas import OmxCommandResult


class UltragoalNativeState(StrEnum):
    """Native OMX UltraGoal availability and status states."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    STATUS_FAILED = "status_failed"


class UltragoalStatusResult(StrictSchemaModel):
    """Represents one read-only native OMX UltraGoal status probe."""

    state: UltragoalNativeState
    supported: bool
    capability_command: tuple[NonEmptyString, ...]
    capability_result: OmxCommandResult
    status_command: tuple[NonEmptyString, ...]
    status_result: OmxCommandResult | None = None
    cwd: NonEmptyString | None = None
    warnings: tuple[NonEmptyString, ...] = ()
