from typing import Literal

from pydantic import Field

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)
from omx_remote.schemas.invoke_schemas import OmxCommandResult


class TeamStatusRequest(StrictSchemaModel):
    """Represents the typed request boundary for team status reads."""

    team_name: NonEmptyString


class TeamAwaitRequest(StrictSchemaModel):
    """Represents the typed request boundary for team await reads."""

    team_name: NonEmptyString


class TeamStatusSnapshot(StrictSchemaModel):
    """Represents the normalized team-status surface."""

    team_name: NonEmptyString
    status: NonEmptyString
    phase: NonEmptyString | None = None
    dead_workers: list[NonEmptyString] = Field(default_factory=list)
    non_reporting_workers: list[NonEmptyString] = Field(default_factory=list)


class TeamAwaitSnapshot(StrictSchemaModel):
    """Represents the normalized team-await surface."""

    team_name: NonEmptyString
    status: NonEmptyString
    cursor: NonEmptyString | None = None
    event_type: NonEmptyString | None = None
    event_worker: NonEmptyString | None = None
    event_task_id: NonEmptyString | None = None


class TeamApiListTasksRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task listing."""

    team_name: NonEmptyString


class TeamApiTaskSnapshot(StrictSchemaModel):
    """Represents a normalized team-api task summary."""

    id: NonEmptyString
    subject: NonEmptyString
    status: NonEmptyString
    owner: NonEmptyString | None = None


class TeamApiListTasksSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api task listing."""

    count: int
    tasks: list[TeamApiTaskSnapshot]


class TeamApiReadEventsRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api event reads."""

    team_name: NonEmptyString


class TeamApiReadMonitorSnapshotRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api monitor snapshot reads."""

    team_name: NonEmptyString


class TeamApiReadConfigRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api config error reads."""

    team_name: NonEmptyString


class TeamApiReadManifestRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api manifest error reads."""

    team_name: NonEmptyString


class TeamApiMailboxListRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api mailbox listing."""

    team_name: NonEmptyString
    worker: NonEmptyString


class TeamApiReadWorkerStatusRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api worker-status reads."""

    team_name: NonEmptyString
    worker: NonEmptyString


class TeamApiSendMessageRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api message delivery."""

    team_name: NonEmptyString
    from_worker: NonEmptyString
    to_worker: NonEmptyString
    body: NonEmptyString


class TeamApiWorkerInboxWriteRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api worker-inbox writes."""

    team_name: NonEmptyString
    worker: NonEmptyString
    content: NonEmptyString


class TeamApiBroadcastRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api broadcast writes."""

    team_name: NonEmptyString
    from_worker: NonEmptyString
    body: NonEmptyString


class TeamApiCreateTaskRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task creation."""

    team_name: NonEmptyString
    subject: NonEmptyString
    description: NonEmptyString
    owner: NonEmptyString | None = None
    blocked_by: list[NonEmptyString] = Field(default_factory=list)
    requires_code_change: bool | None = None


class TeamApiReadTaskRequest(StrictSchemaModel):
    """Represents the typed request boundary for one team-api task read."""

    team_name: NonEmptyString
    task_id: NonEmptyString


class TeamApiTransitionTaskStatusRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task-status transitions."""

    team_name: NonEmptyString
    task_id: NonEmptyString
    from_status: NonEmptyString
    to_status: NonEmptyString
    claim_token: NonEmptyString
    result: NonEmptyString | None = None
    error: NonEmptyString | None = None


class TeamApiUpdateTaskRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task metadata updates."""

    team_name: NonEmptyString
    task_id: NonEmptyString
    subject: NonEmptyString | None = None
    description: NonEmptyString | None = None
    blocked_by: list[NonEmptyString] | None = None
    requires_code_change: bool | None = None


class TeamApiClaimTaskRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task claiming."""

    team_name: NonEmptyString
    task_id: NonEmptyString
    worker: NonEmptyString
    expected_version: int | None = Field(default=None, ge=0)


class TeamApiReleaseTaskClaimRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task-claim release."""

    team_name: NonEmptyString
    task_id: NonEmptyString
    claim_token: NonEmptyString
    worker: NonEmptyString


class TeamApiReadTaskApprovalRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task approval reads."""

    team_name: NonEmptyString
    task_id: NonEmptyString


class TeamApiWriteTaskApprovalRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task approval writes."""

    team_name: NonEmptyString
    task_id: NonEmptyString
    status: NonEmptyString
    reviewer: NonEmptyString
    decision_reason: NonEmptyString
    required: bool | None = None


class TeamApiMailboxMarkDeliveredRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api mailbox delivery marking."""

    team_name: NonEmptyString
    worker: NonEmptyString
    message_id: NonEmptyString


class TeamApiMailboxMarkNotifiedRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api mailbox notification marking."""

    team_name: NonEmptyString
    worker: NonEmptyString
    message_id: NonEmptyString


class TeamApiWriteShutdownRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api shutdown-request writes."""

    team_name: NonEmptyString
    worker: NonEmptyString
    requested_by: NonEmptyString


class TeamApiReadShutdownAckRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api shutdown-ack reads."""

    team_name: NonEmptyString
    worker: NonEmptyString
    min_updated_at: NonEmptyString | None = None


class TeamApiCleanupRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api cleanup requests."""

    team_name: NonEmptyString
    force: bool | None = None
    confirm_issues: bool | None = None


class TeamApiOrphanCleanupRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api orphan cleanup requests."""

    team_name: NonEmptyString


class TeamApiEventSnapshot(StrictSchemaModel):
    """Represents a normalized team-api event summary."""

    type: NonEmptyString
    worker: NonEmptyString | None = None
    task_id: NonEmptyString | None = None
    message_id: NonEmptyString | None = None


class TeamApiReadEventsSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api event reads."""

    count: int
    cursor: str
    events: list[TeamApiEventSnapshot]


class TeamApiReadMonitorSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api monitor snapshot reads."""

    snapshot: object | None = None


class TeamApiReadConfigError(StrictSchemaModel):
    """Represents a typed error envelope for team-api config reads."""

    code: NonEmptyString
    message: NonEmptyString


class TeamApiReadConfigSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api config reads."""

    config: object | None = None


class TeamApiReadManifestError(StrictSchemaModel):
    """Represents a typed error envelope for team-api manifest reads."""

    code: NonEmptyString
    message: NonEmptyString


class TeamApiReadManifestSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api manifest reads."""

    manifest: object | None = None


class TeamApiMailboxMessageSnapshot(StrictSchemaModel):
    """Represents a normalized team-api mailbox message summary."""

    id: NonEmptyString
    subject: NonEmptyString
    body: str
    delivered: bool


class TeamApiMailboxListSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api mailbox listing."""

    worker: NonEmptyString
    count: int
    messages: list[TeamApiMailboxMessageSnapshot]


class TeamApiWorkerStatusSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api worker-status reads."""

    worker: NonEmptyString
    state: NonEmptyString
    updated_at: NonEmptyString


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
    blocked_by: list[NonEmptyString] = Field(default_factory=list)
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
