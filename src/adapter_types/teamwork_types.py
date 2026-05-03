from typing import NotRequired, TypedDict


class TeamApiEnvelopePayload(TypedDict):
    ok: object
    data: object


class TeamApiTransportPayload(TypedDict):
    count: object
    tasks: NotRequired[object]
    cursor: NotRequired[object]
    events: NotRequired[object]


class TeamApiListTasksNormalizedPayload(TypedDict):
    count: object
    tasks: object


class TeamApiReadEventsNormalizedPayload(TypedDict):
    count: object
    cursor: object
    events: object


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


class TeamStatusTransportPayload(TypedDict):
    team_name: object
    status: object
    phase: NotRequired[object]
    current_phase: NotRequired[object]
    dead_workers: NotRequired[object]
    non_reporting_workers: NotRequired[object]


class TeamStatusNormalizedPayload(TypedDict):
    team_name: object
    status: object
    phase: object
    dead_workers: object
    non_reporting_workers: object


class TeamAwaitTransportEventPayload(TypedDict, total=False):
    type: object
    worker: object
    task_id: object


class TeamAwaitTransportPayload(TypedDict):
    team_name: object
    status: object
    cursor: NotRequired[object]
    event: NotRequired[object]


class TeamAwaitNormalizedPayload(TypedDict):
    team_name: object
    status: object
    cursor: object
    event_type: object
    event_worker: object
    event_task_id: object
