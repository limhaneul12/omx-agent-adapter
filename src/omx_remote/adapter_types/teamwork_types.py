from typing import NotRequired, TypedDict

import msgspec


class TeamApiEnvelopeSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded top-level team-api transport envelope."""

    ok: bool | None = None
    data: object = None
    error: object = None


class TeamApiDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested team-api data payload before stable subset normalization."""

    count: object = None
    tasks: object = None
    cursor: object = None
    events: object = None
    worker: object = None
    messages: object = None
    snapshot: object = None
    status: object = None
    config: object = None
    manifest: object = None


class TeamApiErrorSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested team-api error payload before stable subset normalization."""

    code: object = None
    message: object = None


class TeamApiEnvelopePayload(TypedDict):
    """Represents the stable top-level envelope subset for successful team-api payloads."""

    ok: bool
    data: object


class TeamApiErrorTransportPayload(TypedDict):
    """Represents the stable nested error subset for unsuccessful team-api payloads."""

    code: str
    message: str


class TeamApiTransportPayload(TypedDict, total=False):
    """Represents the stable nested `data` subset shared by typed team-api reads."""

    count: int
    tasks: object
    cursor: str
    events: object
    worker: str
    messages: object
    snapshot: object
    status: object
    config: object
    manifest: object


class TeamApiListTasksNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api list-tasks."""

    count: int
    tasks: object


class TeamApiReadEventsNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api read-events."""

    count: int
    cursor: str
    events: object


class TeamApiMailboxListNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api mailbox-list."""

    worker: str
    count: int
    messages: object


class TeamApiWorkerStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api worker status."""

    worker: str
    state: str
    updated_at: str


class TeamApiTransportTaskPayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api task item."""

    id: str
    subject: str
    title: str
    status: str
    owner: str
    assignee: str


class TeamApiTransportEventPayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api event item."""

    type: str
    worker: str
    task_id: str
    message_id: str | None


class TeamApiTransportMailboxMessagePayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api mailbox message item."""

    id: str
    subject: str
    body: str
    delivered: bool


class TeamApiTransportWorkerStatusPayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api worker-status item."""

    state: str
    updated_at: str


class TeamStatusSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded `omx team status` transport payload."""

    team_name: object = None
    status: object = None
    phase: object = None
    current_phase: object = None
    dead_workers: object = None
    non_reporting_workers: object = None


class TeamAwaitEventSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested `omx team await` event payload."""

    type: object = None
    worker: object = None
    task_id: object = None


class TeamAwaitSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded `omx team await` transport payload."""

    team_name: object = None
    status: object = None
    cursor: object = None
    event: object = None


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
