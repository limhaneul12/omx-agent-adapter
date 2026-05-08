from typing_extensions import TypedDict

from omx_remote.adapter_types.json_types import JsonValue


class TeamApiRawTaskPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents one raw team-api task item with variable upstream metadata."""

    id: str
    subject: str
    title: str
    status: str
    owner: str
    assignee: str


class TeamApiRawEventPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents one raw team-api event item with variable upstream metadata."""

    type: str
    worker: str
    task_id: str
    message_id: str | None


class TeamApiRawMailboxMessagePayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents one raw team-api mailbox message item with variable upstream metadata."""

    id: str
    subject: str
    body: str
    delivered: bool


class TeamApiRawWorkerStatusPayload(TypedDict, total=False, extra_items=JsonValue):
    """Represents one raw worker-status mapping with variable upstream metadata."""

    state: str
    updated_at: str
