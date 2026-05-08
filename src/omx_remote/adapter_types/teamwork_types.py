from typing import NotRequired

import msgspec
from typing_extensions import TypedDict


class TeamApiEnvelopeSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded top-level team-api transport envelope."""

    ok: bool
    # The ok flag selects the operation-specific data/error loader that narrows this.
    data: object = None
    error: object = None


class TeamApiRawTaskPayload(TypedDict, total=False, extra_items=object):
    """Represents one raw team-api task item with variable upstream metadata."""

    id: str
    subject: str
    title: str
    status: str
    owner: str
    assignee: str


class TeamApiRawEventPayload(TypedDict, total=False, extra_items=object):
    """Represents one raw team-api event item with variable upstream metadata."""

    type: str
    worker: str
    task_id: str
    message_id: str | None


class TeamApiRawMailboxMessagePayload(TypedDict, total=False, extra_items=object):
    """Represents one raw team-api mailbox message item with variable upstream metadata."""

    id: str
    subject: str
    body: str
    delivered: bool


class TeamApiRawWorkerStatusPayload(TypedDict, total=False, extra_items=object):
    """Represents one raw worker-status object with variable upstream metadata."""

    state: str
    updated_at: str


class TeamApiListTasksDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api list-tasks`."""

    count: int
    tasks: list[TeamApiRawTaskPayload]


class TeamApiReadEventsDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-events`."""

    count: int
    cursor: str
    events: list[TeamApiRawEventPayload]


class TeamApiMailboxListDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api mailbox-list`."""

    worker: str
    count: int
    messages: list[TeamApiRawMailboxMessagePayload]


class TeamApiReadMonitorSnapshotDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-monitor-snapshot`."""

    # Monitor snapshots are upstream-authored JSON objects with no stable subset yet.
    snapshot: object | None = None


class TeamApiReadConfigDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-config`."""

    # Config is a runtime-authored JSON object whose nested shape is not stable here.
    config: dict[str, object] | None = None


class TeamApiReadWorkerStatusDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-worker-status`."""

    worker: str
    status: TeamApiRawWorkerStatusPayload


class TeamApiErrorSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested team-api error payload before stable subset normalization."""

    code: str
    message: str


class TeamApiEnvelopePayload(TypedDict, extra_items=object):
    """Represents the stable top-level envelope subset for successful team-api payloads."""

    ok: bool
    # The nested operation payload is selected and narrowed by each concrete loader.
    data: dict[str, object]


class TeamApiErrorTransportPayload(TypedDict, closed=True):
    """Represents the stable nested error subset for unsuccessful team-api payloads."""

    code: str
    message: str


class TeamApiTransportPayload(TypedDict, total=False, extra_items=object):
    """Represents the stable nested `data` subset shared by typed team-api reads."""

    count: int
    tasks: list[TeamApiRawTaskPayload]
    cursor: str
    events: list[TeamApiRawEventPayload]
    worker: str
    messages: list[TeamApiRawMailboxMessagePayload]
    # Monitor/config/manifest bodies remain dynamic at the transport seam.
    snapshot: object
    status: TeamApiRawWorkerStatusPayload
    config: dict[str, object]
    manifest: dict[str, object]


class TeamApiListTasksTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api list-tasks`."""

    count: int
    tasks: list[TeamApiRawTaskPayload]


class TeamApiReadEventsTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-events`."""

    count: int
    cursor: str
    events: list[TeamApiRawEventPayload]


class TeamApiMailboxListTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api mailbox-list`."""

    worker: str
    count: int
    messages: list[TeamApiRawMailboxMessagePayload]


class TeamApiReadMonitorSnapshotTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-monitor-snapshot`."""

    snapshot: object | None


class TeamApiReadConfigTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-config`."""

    # Config is intentionally broad until the team-api config contract stabilizes.
    config: dict[str, object] | None


class TeamApiReadWorkerStatusTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-worker-status`."""

    worker: str
    status: TeamApiRawWorkerStatusPayload


class TeamApiWorkerStatusNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for team-api worker status."""

    worker: str
    state: str
    updated_at: str


class TeamApiTransportTaskPayload(TypedDict, total=False, closed=True):
    """Represents the stable observed subset for one team-api task item."""

    id: str
    subject: str
    title: str
    status: str
    owner: str
    assignee: str


class TeamApiTransportEventPayload(TypedDict, total=False, closed=True):
    """Represents the stable observed subset for one team-api event item."""

    type: str
    worker: str
    task_id: str
    message_id: str | None


class TeamApiTransportMailboxMessagePayload(TypedDict, total=False, closed=True):
    """Represents the stable observed subset for one team-api mailbox message item."""

    id: str
    subject: str
    body: str
    delivered: bool


class TeamApiTransportWorkerStatusPayload(TypedDict, total=False, closed=True):
    """Represents the stable observed subset for one team-api worker-status item."""

    state: str
    updated_at: str


class TeamApiListTasksNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for team-api list-tasks."""

    count: int
    tasks: list[TeamApiTransportTaskPayload]


class TeamApiReadEventsNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for team-api read-events."""

    count: int
    cursor: str
    events: list[TeamApiTransportEventPayload]


class TeamApiMailboxListNormalizedPayload(TypedDict, closed=True):
    """Represents the normalized adapter-owned payload for team-api mailbox-list."""

    worker: str
    count: int
    messages: list[TeamApiTransportMailboxMessagePayload]


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
