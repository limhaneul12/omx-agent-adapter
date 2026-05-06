from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class TeamApiTaskSnapshot(StrictSchemaModel):
    """Represents a normalized team-api task summary."""

    id: NonEmptyString
    subject: NonEmptyString
    status: NonEmptyString
    owner: NonEmptyString | None = None


type TeamApiTaskSnapshots = tuple[TeamApiTaskSnapshot, ...]


class TeamApiListTasksSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api task listing."""

    count: int
    tasks: TeamApiTaskSnapshots


class TeamApiEventSnapshot(StrictSchemaModel):
    """Represents a normalized team-api event summary."""

    type: NonEmptyString
    worker: NonEmptyString | None = None
    task_id: NonEmptyString | None = None
    message_id: NonEmptyString | None = None


type TeamApiEventSnapshots = tuple[TeamApiEventSnapshot, ...]


class TeamApiReadEventsSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api event reads."""

    count: int
    cursor: str
    events: TeamApiEventSnapshots


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


type TeamApiMailboxMessageSnapshots = tuple[TeamApiMailboxMessageSnapshot, ...]


class TeamApiMailboxListSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api mailbox listing."""

    worker: NonEmptyString
    count: int
    messages: TeamApiMailboxMessageSnapshots


class TeamApiWorkerStatusSnapshot(StrictSchemaModel):
    """Represents the normalized result for team-api worker-status reads."""

    worker: NonEmptyString
    state: NonEmptyString
    updated_at: NonEmptyString
