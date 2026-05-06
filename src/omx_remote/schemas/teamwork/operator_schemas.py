from typing import Literal

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult


class TeamOperatorDispatchInstructionRequest(StrictSchemaModel):
    """Represents one Hermes-oriented instruction-dispatch request."""

    team_name: NonEmptyString
    from_worker: NonEmptyString
    body: NonEmptyString
    to_worker: NonEmptyString | None = None
    durable_delivery: bool = False


class TeamOperatorDispatchTaskRequest(StrictSchemaModel):
    """Represents one Hermes-oriented task-dispatch request."""

    team_name: NonEmptyString
    subject: NonEmptyString
    description: NonEmptyString
    owner: NonEmptyString | None = None
    blocked_by: NonEmptyStrings = ()
    requires_code_change: bool | None = None


class TeamOperatorTaskApprovalRequest(StrictSchemaModel):
    """Represents one Hermes-oriented task-approval request."""

    team_name: NonEmptyString
    task_id: NonEmptyString
    status: NonEmptyString
    reviewer: NonEmptyString
    decision_reason: NonEmptyString
    required: bool | None = None


class TeamOperatorWorkerRecheckRequest(StrictSchemaModel):
    """Represents one Hermes-oriented worker recheck request."""

    team_name: NonEmptyString
    from_worker: NonEmptyString
    worker: NonEmptyString
    body: NonEmptyString


class TeamOperatorDispatchOutcome(StrictSchemaModel):
    """Represents the Hermes-oriented outcome for one dispatched operator action."""

    selected_operation: Literal[
        "send-message",
        "write-worker-inbox",
        "broadcast",
        "create-task",
        "write-task-approval",
    ]
    outcome: Literal["accepted", "accepted_but_unverified", "failed"]
    needs_follow_up: bool
    reason: NonEmptyString
    command_result: OmxCommandResult


class TeamOperatorWorkerFollowUpOutcome(StrictSchemaModel):
    """Represents the Hermes-oriented outcome for one worker follow-up decision."""

    worker_state: NonEmptyString
    selected_delivery_mode: Literal["direct_message", "durable_inbox"]
    dispatch_result: TeamOperatorDispatchOutcome
