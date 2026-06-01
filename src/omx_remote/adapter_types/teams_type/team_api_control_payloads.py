"""Typed outbound payload contracts for mutating Team API control calls."""

import msgspec

type TeamApiStringItems = tuple[str, ...]
type TeamApiOptionalString = str | msgspec.UnsetType
type TeamApiOptionalBool = bool | msgspec.UnsetType
type TeamApiOptionalInt = int | msgspec.UnsetType
type TeamApiOptionalStringItems = TeamApiStringItems | msgspec.UnsetType


class TeamApiSendMessagePayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api send-message`."""

    team_name: str
    from_worker: str
    to_worker: str
    body: str


class TeamApiWorkerInboxWritePayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api write-worker-inbox`."""

    team_name: str
    worker: str
    content: str


class TeamApiBroadcastPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api broadcast`."""

    team_name: str
    from_worker: str
    body: str


class TeamApiCreateTaskPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api create-task`."""

    team_name: str
    subject: str
    description: str
    owner: TeamApiOptionalString = msgspec.UNSET
    blocked_by: TeamApiOptionalStringItems = msgspec.UNSET
    requires_code_change: TeamApiOptionalBool = msgspec.UNSET


class TeamApiReadTaskPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api read-task`."""

    team_name: str
    task_id: str


class TeamApiTransitionTaskStatusPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api transition-task-status`."""

    team_name: str
    task_id: str
    from_status: str = msgspec.field(name="from")
    to_status: str = msgspec.field(name="to")
    claim_token: str
    result: TeamApiOptionalString = msgspec.UNSET
    error: TeamApiOptionalString = msgspec.UNSET


class TeamApiUpdateTaskPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api update-task`."""

    team_name: str
    task_id: str
    subject: TeamApiOptionalString = msgspec.UNSET
    description: TeamApiOptionalString = msgspec.UNSET
    blocked_by: TeamApiOptionalStringItems = msgspec.UNSET
    requires_code_change: TeamApiOptionalBool = msgspec.UNSET


class TeamApiClaimTaskPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api claim-task`."""

    team_name: str
    task_id: str
    worker: str
    expected_version: TeamApiOptionalInt = msgspec.UNSET


class TeamApiReleaseTaskClaimPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api release-task-claim`."""

    team_name: str
    task_id: str
    claim_token: str
    worker: str


class TeamApiReadTaskApprovalPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api read-task-approval`."""

    team_name: str
    task_id: str


class TeamApiWriteTaskApprovalPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api write-task-approval`."""

    team_name: str
    task_id: str
    status: str
    reviewer: str
    decision_reason: str
    required: TeamApiOptionalBool = msgspec.UNSET


class TeamApiMailboxMarkDeliveredPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api mailbox-mark-delivered`."""

    team_name: str
    worker: str
    message_id: str


class TeamApiMailboxMarkNotifiedPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api mailbox-mark-notified`."""

    team_name: str
    worker: str
    message_id: str


class TeamApiWriteShutdownPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api write-shutdown-request`."""

    team_name: str
    worker: str
    requested_by: str


class TeamApiReadShutdownAckPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api read-shutdown-ack`."""

    team_name: str
    worker: str
    min_updated_at: TeamApiOptionalString = msgspec.UNSET


class TeamApiCleanupPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api cleanup`."""

    team_name: str
    force: TeamApiOptionalBool = msgspec.UNSET
    confirm_issues: TeamApiOptionalBool = msgspec.UNSET


class TeamApiOrphanCleanupPayload(msgspec.Struct, frozen=True, kw_only=True):
    """Represents the payload for `omx team api orphan-cleanup`."""

    team_name: str


type TeamApiControlPayload = (
    TeamApiSendMessagePayload
    | TeamApiWorkerInboxWritePayload
    | TeamApiBroadcastPayload
    | TeamApiCreateTaskPayload
    | TeamApiReadTaskPayload
    | TeamApiTransitionTaskStatusPayload
    | TeamApiUpdateTaskPayload
    | TeamApiClaimTaskPayload
    | TeamApiReleaseTaskClaimPayload
    | TeamApiReadTaskApprovalPayload
    | TeamApiWriteTaskApprovalPayload
    | TeamApiMailboxMarkDeliveredPayload
    | TeamApiMailboxMarkNotifiedPayload
    | TeamApiWriteShutdownPayload
    | TeamApiReadShutdownAckPayload
    | TeamApiCleanupPayload
    | TeamApiOrphanCleanupPayload
)
