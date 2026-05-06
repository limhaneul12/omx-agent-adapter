from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult
from omx_remote.shared.omx_enums.operator_enums import (
    OperatorLane,
    OperatorLoopState,
    OperatorNextAction,
)


class OperatorRecoveryHint(StrictSchemaModel):
    """Represents one typed recovery hint for the standardized operator loop."""

    next_action: OperatorNextAction
    reason: NonEmptyString
    cleanup_first: bool = False


class OperatorActionResult(StrictSchemaModel):
    """Represents one standardized operator-loop outcome."""

    lane: OperatorLane
    action: NonEmptyString
    loop_state: OperatorLoopState
    next_action: OperatorNextAction
    summary: NonEmptyString
    recovery_hint: OperatorRecoveryHint | None = None
    command_result: OmxCommandResult | None = None
