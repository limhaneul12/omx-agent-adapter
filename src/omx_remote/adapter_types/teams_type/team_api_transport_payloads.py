from typing_extensions import TypedDict

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.adapter_types.teams_type.team_api_raw_payloads import (
    TeamApiRawEventPayload,
    TeamApiRawMailboxMessagePayload,
    TeamApiRawTaskPayload,
    TeamApiRawWorkerStatusPayload,
)


class TeamApiEnvelopePayload(TypedDict, extra_items=JsonValue):
    """Represents the stable top-level envelope subset for successful team-api payloads."""

    ok: bool
    # The nested operation payload is selected and narrowed by each concrete loader.
    data: JsonObject


class TeamApiErrorTransportPayload(TypedDict, closed=True):
    """Represents the stable nested error subset for unsuccessful team-api payloads."""

    code: str
    message: str


class TeamApiTransportPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents the stable nested `data` subset shared by typed team-api reads."""

    count: int
    tasks: list[TeamApiRawTaskPayload]
    cursor: str
    events: list[TeamApiRawEventPayload]
    worker: str
    messages: list[TeamApiRawMailboxMessagePayload]
    # Monitor/config/manifest bodies remain dynamic JSON at the transport seam.
    snapshot: JsonValue
    status: TeamApiRawWorkerStatusPayload
    config: JsonObject
    manifest: JsonObject


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

    snapshot: JsonValue


class TeamApiReadConfigTransportPayload(TypedDict, closed=True):
    """Represents the loaded data payload for `omx team api read-config`."""

    # Config is intentionally broad until the team-api config contract stabilizes.
    config: JsonObject | None


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
