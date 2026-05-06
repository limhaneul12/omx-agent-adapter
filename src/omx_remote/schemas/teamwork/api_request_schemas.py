from pydantic import Field

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)


class TeamApiListTasksRequest(StrictSchemaModel):
    """Represents the typed request boundary for team-api task listing."""

    team_name: NonEmptyString


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
    blocked_by: NonEmptyStrings = ()
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
    blocked_by: NonEmptyStrings | None = None
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
