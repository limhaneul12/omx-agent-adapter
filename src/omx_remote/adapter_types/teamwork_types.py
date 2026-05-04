from typing import NotRequired, Required, TypedDict


class TeamApiEnvelopePayload(TypedDict):
    ok: Required[bool]
    data: Required[object]


class TeamApiErrorTransportPayload(TypedDict):
    code: Required[str]
    message: Required[str]


class TeamApiTransportPayload(TypedDict):
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
    count: Required[int]
    tasks: Required[object]


class TeamApiReadEventsNormalizedPayload(TypedDict):
    count: Required[int]
    cursor: Required[str]
    events: Required[object]


class TeamApiMailboxListNormalizedPayload(TypedDict):
    worker: Required[str]
    count: Required[int]
    messages: Required[object]


class TeamApiWorkerStatusNormalizedPayload(TypedDict):
    worker: Required[str]
    state: Required[str]
    updated_at: Required[str]


class TeamApiTransportTaskPayload(TypedDict, total=False):
    id: NotRequired[str]
    subject: NotRequired[str]
    title: NotRequired[str]
    status: NotRequired[str]
    owner: NotRequired[str]
    assignee: NotRequired[str]


class TeamApiTransportEventPayload(TypedDict, total=False):
    type: NotRequired[str]
    worker: NotRequired[str]
    task_id: NotRequired[str]
    message_id: NotRequired[str | None]


class TeamApiTransportMailboxMessagePayload(TypedDict, total=False):
    id: NotRequired[str]
    subject: NotRequired[str]
    body: NotRequired[str]
    delivered: NotRequired[bool]


class TeamApiTransportWorkerStatusPayload(TypedDict, total=False):
    state: NotRequired[str]
    updated_at: NotRequired[str]


class TeamStatusTransportPayload(TypedDict):
    team_name: Required[str]
    status: Required[str]
    phase: NotRequired[str | None]
    current_phase: NotRequired[str | None]
    dead_workers: NotRequired[list[str]]
    non_reporting_workers: NotRequired[list[str]]


class TeamStatusNormalizedPayload(TypedDict):
    team_name: Required[str]
    status: Required[str]
    phase: Required[str | None]
    dead_workers: Required[list[str]]
    non_reporting_workers: Required[list[str]]


class TeamAwaitTransportEventPayload(TypedDict, total=False):
    type: NotRequired[str]
    worker: NotRequired[str]
    task_id: NotRequired[str]


class TeamAwaitTransportPayload(TypedDict):
    team_name: Required[str]
    status: Required[str]
    cursor: NotRequired[str]
    event: NotRequired[TeamAwaitTransportEventPayload | None]


class TeamAwaitNormalizedPayload(TypedDict):
    team_name: Required[str]
    status: Required[str]
    cursor: Required[str | None]
    event_type: Required[str | None]
    event_worker: Required[str | None]
    event_task_id: Required[str | None]
