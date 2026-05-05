from pydantic import Field

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)


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
