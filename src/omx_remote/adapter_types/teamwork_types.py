from typing import NotRequired

import msgspec
from typing_extensions import TypedDict


class TeamApiEnvelopeSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded top-level team-api transport envelope."""

    ok: bool
    data: object = None
    error: object = None


class TeamApiListTasksDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api list-tasks`."""

    count: int
    # Task items carry variable upstream metadata and are narrowed by normalizers.
    tasks: list[object]


class TeamApiReadEventsDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-events`."""

    count: int
    cursor: str
    # Event items carry operation-specific extras and are narrowed by normalizers.
    events: list[object]


class TeamApiMailboxListDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api mailbox-list`."""

    worker: str
    count: int
    # Mailbox items carry upstream extras and are narrowed by normalizers.
    messages: list[object]


class TeamApiReadMonitorSnapshotDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-monitor-snapshot`."""

    snapshot: object | None = None


class TeamApiReadConfigDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-config`."""

    config: dict[str, object] | None = None


class TeamApiReadWorkerStatusDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-worker-status`."""

    worker: str
    status: dict[str, object]


class TeamApiErrorSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested team-api error payload before stable subset normalization."""

    code: str
    message: str


class TeamApiEnvelopePayload(TypedDict, extra_items=object):
    """Represents the stable top-level envelope subset for successful team-api payloads."""

    ok: bool
    data: dict[str, object]


class TeamApiErrorTransportPayload(TypedDict, closed=True):
    """Represents the stable nested error subset for unsuccessful team-api payloads."""

    code: str
    message: str


class TeamApiTransportPayload(TypedDict, total=False, extra_items=object):
    """Represents the stable nested `data` subset shared by typed team-api reads."""

    count: int
    tasks: list[object]
    cursor: str
    events: list[object]
    worker: str
    messages: list[object]
    snapshot: object
    status: dict[str, object]
    config: dict[str, object]
    manifest: dict[str, object]


class TeamApiListTasksTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api list-tasks`."""

    count: int
    tasks: list[object]


class TeamApiReadEventsTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-events`."""

    count: int
    cursor: str
    events: list[object]


class TeamApiMailboxListTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api mailbox-list`."""

    worker: str
    count: int
    messages: list[object]


class TeamApiReadMonitorSnapshotTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-monitor-snapshot`."""

    snapshot: object | None


class TeamApiReadConfigTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-config`."""

    config: dict[str, object] | None


class TeamApiReadWorkerStatusTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-worker-status`."""

    worker: str
    status: dict[str, object]


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
