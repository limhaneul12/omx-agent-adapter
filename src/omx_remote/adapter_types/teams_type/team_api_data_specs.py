import msgspec

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.adapter_types.teams_type.team_api_raw_payloads import (
    TeamApiRawEventPayload,
    TeamApiRawMailboxMessagePayload,
    TeamApiRawTaskPayload,
    TeamApiRawWorkerStatusPayload,
)


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

    # Monitor snapshots are upstream-authored JSON values with no stable subset yet.
    snapshot: JsonValue = None


class TeamApiReadConfigDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-config`."""

    # Config is a runtime-authored JSON mapping whose nested shape is not stable here.
    config: JsonObject | None = None


class TeamApiReadWorkerStatusDataSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded data payload for `omx team api read-worker-status`."""

    worker: str
    status: TeamApiRawWorkerStatusPayload


class TeamApiErrorSpec(msgspec.Struct, kw_only=True):
    """Represents the decoded nested team-api error payload before stable subset normalization."""

    code: str
    message: str
