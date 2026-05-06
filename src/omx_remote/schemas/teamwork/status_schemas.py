from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
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
    dead_workers: NonEmptyStrings = ()
    non_reporting_workers: NonEmptyStrings = ()


class TeamAwaitSnapshot(StrictSchemaModel):
    """Represents the normalized team-await surface."""

    team_name: NonEmptyString
    status: NonEmptyString
    cursor: NonEmptyString | None = None
    event_type: NonEmptyString | None = None
    event_worker: NonEmptyString | None = None
    event_task_id: NonEmptyString | None = None
