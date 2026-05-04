from pydantic import BaseModel, ConfigDict, Field

from omx_remote.schemas.common_schemas import NonEmptyString


class TeamStatusRequest(BaseModel):
    """Represents the typed request boundary for team status reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamAwaitRequest(BaseModel):
    """Represents the typed request boundary for team await reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamStatusSnapshot(BaseModel):
    """Represents the normalized team-status surface."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString
    status: NonEmptyString
    phase: NonEmptyString | None = None
    dead_workers: list[NonEmptyString] = Field(default_factory=list)
    non_reporting_workers: list[NonEmptyString] = Field(default_factory=list)


class TeamAwaitSnapshot(BaseModel):
    """Represents the normalized team-await surface."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString
    status: NonEmptyString
    cursor: NonEmptyString | None = None
    event_type: NonEmptyString | None = None
    event_worker: NonEmptyString | None = None
    event_task_id: NonEmptyString | None = None


class TeamApiListTasksRequest(BaseModel):
    """Represents the typed request boundary for team-api task listing."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamApiTaskSnapshot(BaseModel):
    """Represents a normalized team-api task summary."""

    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    subject: NonEmptyString
    status: NonEmptyString
    owner: NonEmptyString | None = None


class TeamApiListTasksSnapshot(BaseModel):
    """Represents the normalized result for team-api task listing."""

    model_config = ConfigDict(extra="forbid")

    count: int
    tasks: list[TeamApiTaskSnapshot]


class TeamApiReadEventsRequest(BaseModel):
    """Represents the typed request boundary for team-api event reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamApiReadMonitorSnapshotRequest(BaseModel):
    """Represents the typed request boundary for team-api monitor snapshot reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamApiReadConfigRequest(BaseModel):
    """Represents the typed request boundary for team-api config error reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamApiReadManifestRequest(BaseModel):
    """Represents the typed request boundary for team-api manifest error reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class TeamApiMailboxListRequest(BaseModel):
    """Represents the typed request boundary for team-api mailbox listing."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString
    worker: NonEmptyString


class TeamApiEventSnapshot(BaseModel):
    """Represents a normalized team-api event summary."""

    model_config = ConfigDict(extra="forbid")

    type: NonEmptyString
    worker: NonEmptyString | None = None
    task_id: NonEmptyString | None = None
    message_id: NonEmptyString | None = None


class TeamApiReadEventsSnapshot(BaseModel):
    """Represents the normalized result for team-api event reads."""

    model_config = ConfigDict(extra="forbid")

    count: int
    cursor: str
    events: list[TeamApiEventSnapshot]


class TeamApiReadMonitorSnapshot(BaseModel):
    """Represents the normalized result for team-api monitor snapshot reads."""

    model_config = ConfigDict(extra="forbid")

    snapshot: object | None = None


class TeamApiReadConfigError(BaseModel):
    """Represents a typed error envelope for team-api config reads."""

    model_config = ConfigDict(extra="forbid")

    code: NonEmptyString
    message: NonEmptyString


class TeamApiReadConfigSnapshot(BaseModel):
    """Represents the normalized result for team-api config reads."""

    model_config = ConfigDict(extra="forbid")

    config: object | None = None


class TeamApiReadManifestError(BaseModel):
    """Represents a typed error envelope for team-api manifest reads."""

    model_config = ConfigDict(extra="forbid")

    code: NonEmptyString
    message: NonEmptyString


class TeamApiReadManifestSnapshot(BaseModel):
    """Represents the normalized result for team-api manifest reads."""

    model_config = ConfigDict(extra="forbid")

    manifest: object | None = None


class TeamApiReadWorkerStatusRequest(BaseModel):
    """Represents the typed request boundary for team-api worker-status reads."""

    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString
    worker: NonEmptyString


class TeamApiMailboxMessageSnapshot(BaseModel):
    """Represents a normalized team-api mailbox message summary."""

    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    subject: NonEmptyString
    body: str
    delivered: bool


class TeamApiMailboxListSnapshot(BaseModel):
    """Represents the normalized result for team-api mailbox listing."""

    model_config = ConfigDict(extra="forbid")

    worker: NonEmptyString
    count: int
    messages: list[TeamApiMailboxMessageSnapshot]


class TeamApiWorkerStatusSnapshot(BaseModel):
    """Represents the normalized result for team-api worker-status reads."""

    model_config = ConfigDict(extra="forbid")

    worker: NonEmptyString
    state: NonEmptyString
    updated_at: NonEmptyString
