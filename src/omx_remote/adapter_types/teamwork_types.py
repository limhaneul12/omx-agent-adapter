from typing import NotRequired, Required, TypedDict


class TeamApiEnvelopePayload(TypedDict):
    """Represents the stable top-level envelope subset for successful team-api payloads."""

    ok: Required[bool]
    data: Required[object]


class TeamApiErrorTransportPayload(TypedDict):
    """Represents the stable nested error subset for unsuccessful team-api payloads."""

    code: Required[str]
    message: Required[str]


class TeamApiTransportPayload(TypedDict):
    """Represents the stable nested `data` subset shared by typed team-api reads."""

    count: NotRequired[int]
    tasks: NotRequired[object]
    cursor: NotRequired[str]
    events: NotRequired[object]
    worker: NotRequired[str]
    messages: NotRequired[object]
    snapshot: NotRequired[object]
    status: NotRequired[object]
    config: NotRequired[object]
    manifest: NotRequired[object]


class TeamApiListTasksNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api list-tasks."""

    count: Required[int]
    tasks: Required[object]


class TeamApiReadEventsNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api read-events."""

    count: Required[int]
    cursor: Required[str]
    events: Required[object]


class TeamApiMailboxListNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api mailbox-list."""

    worker: Required[str]
    count: Required[int]
    messages: Required[object]


class TeamApiWorkerStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team-api worker status."""

    worker: Required[str]
    state: Required[str]
    updated_at: Required[str]


class TeamApiTransportTaskPayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api task item."""

    id: NotRequired[str]
    subject: NotRequired[str]
    title: NotRequired[str]
    status: NotRequired[str]
    owner: NotRequired[str]
    assignee: NotRequired[str]


class TeamApiTransportEventPayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api event item."""

    type: NotRequired[str]
    worker: NotRequired[str]
    task_id: NotRequired[str]
    message_id: NotRequired[str | None]


class TeamApiTransportMailboxMessagePayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api mailbox message item."""

    id: NotRequired[str]
    subject: NotRequired[str]
    body: NotRequired[str]
    delivered: NotRequired[bool]


class TeamApiTransportWorkerStatusPayload(TypedDict, total=False):
    """Represents the stable observed subset for one team-api worker-status item."""

    state: NotRequired[str]
    updated_at: NotRequired[str]


class TeamStatusTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for `omx team status`."""

    team_name: Required[str]
    status: Required[str]
    phase: NotRequired[str | None]
    current_phase: NotRequired[str | None]
    dead_workers: NotRequired[list[str]]
    non_reporting_workers: NotRequired[list[str]]


class TeamStatusNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team status."""

    team_name: Required[str]
    status: Required[str]
    phase: Required[str | None]
    dead_workers: Required[list[str]]
    non_reporting_workers: Required[list[str]]


class TeamAwaitTransportEventPayload(TypedDict, total=False):
    """Represents the stable observed event subset nested under `omx team await`."""

    type: NotRequired[str]
    worker: NotRequired[str]
    task_id: NotRequired[str]


class TeamAwaitTransportPayload(TypedDict):
    """Represents the stable top-level transport subset for `omx team await`."""

    team_name: Required[str]
    status: Required[str]
    cursor: NotRequired[str]
    event: NotRequired[TeamAwaitTransportEventPayload | None]


class TeamAwaitNormalizedPayload(TypedDict):
    """Represents the normalized adapter-owned payload for team await snapshots."""

    team_name: Required[str]
    status: Required[str]
    cursor: Required[str | None]
    event_type: Required[str | None]
    event_worker: Required[str | None]
    event_task_id: Required[str | None]
