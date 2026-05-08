from typing import NotRequired

import msgspec
from typing_extensions import TypedDict


class TeamStatusSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded `omx team status` transport payload."""

    team_name: str
    status: str
    phase: str | None = None
    current_phase: str | None = None
    dead_workers: list[str] | None = None
    non_reporting_workers: list[str] | None = None


class TeamAwaitEventSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested `omx team await` event payload."""

    type: str | None = None
    worker: str | None = None
    task_id: str | None = None


class TeamAwaitSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded `omx team await` transport payload."""

    team_name: str
    status: str
    cursor: str | None = None
    event: TeamAwaitEventSpec | None = None


class TeamStatusTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for `omx team status`."""

    team_name: str
    status: str
    phase: NotRequired[str | None]
    current_phase: NotRequired[str | None]
    dead_workers: NotRequired[list[str]]
    non_reporting_workers: NotRequired[list[str]]


class TeamStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team status."""

    team_name: str
    status: str
    phase: str | None
    dead_workers: list[str]
    non_reporting_workers: list[str]


class TeamAwaitTransportEventPayload(TypedDict, total=False):
    """Represents the stable observed event subset nested under `omx team await`."""

    type: str
    worker: str
    task_id: str


class TeamAwaitTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for `omx team await`."""

    team_name: str
    status: str
    cursor: NotRequired[str]
    event: NotRequired[TeamAwaitTransportEventPayload | None]


class TeamAwaitNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team await snapshots."""

    team_name: str
    status: str
    cursor: str | None
    event_type: str | None
    event_worker: str | None
    event_task_id: str | None
