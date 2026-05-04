from typing import NotRequired, Required, TypedDict


class TeamApiEnvelopePayload(TypedDict):
    ok: Required[bool]
    data: Required[object]


class TeamApiErrorTransportPayload(TypedDict):
    code: Required[object]
    message: Required[object]


class TeamApiTransportPayload(TypedDict):
    count: NotRequired[object]
    tasks: NotRequired[object]
    cursor: NotRequired[object]
    events: NotRequired[object]
    worker: NotRequired[object]
    messages: NotRequired[object]
    snapshot: NotRequired[object]


class TeamApiListTasksNormalizedPayload(TypedDict):
    count: Required[object]
    tasks: Required[object]


class TeamApiReadEventsNormalizedPayload(TypedDict):
    count: Required[object]
    cursor: Required[object]
    events: Required[object]


class TeamApiMailboxListNormalizedPayload(TypedDict):
    worker: Required[object]
    count: Required[object]
    messages: Required[object]


class TeamApiTransportTaskPayload(TypedDict, total=False):
    id: object
    subject: object
    title: object
    status: object
    owner: object
    assignee: object


class TeamApiTransportEventPayload(TypedDict, total=False):
    type: object
    worker: object
    task_id: object
    message_id: object


class TeamApiTransportMailboxMessagePayload(TypedDict, total=False):
    id: object
    subject: object
    body: object
    delivered: object


class TeamStatusTransportPayload(TypedDict):
    team_name: Required[object]
    status: Required[object]
    phase: NotRequired[object]
    current_phase: NotRequired[object]
    dead_workers: NotRequired[object]
    non_reporting_workers: NotRequired[object]


class TeamStatusNormalizedPayload(TypedDict):
    team_name: Required[object]
    status: Required[object]
    phase: Required[object]
    dead_workers: Required[object]
    non_reporting_workers: Required[object]


class TeamAwaitTransportEventPayload(TypedDict, total=False):
    type: object
    worker: object
    task_id: object


class TeamAwaitTransportPayload(TypedDict):
    team_name: Required[object]
    status: Required[object]
    cursor: NotRequired[object]
    event: NotRequired[object]


class TeamAwaitNormalizedPayload(TypedDict):
    team_name: Required[object]
    status: Required[object]
    cursor: Required[object]
    event_type: Required[object]
    event_worker: Required[object]
    event_task_id: Required[object]
