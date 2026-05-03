from pydantic import BaseModel, ConfigDict, Field

from schemas.common_schemas import NonEmptyString


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
