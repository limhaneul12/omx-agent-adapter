from enum import StrEnum


class TeamEventType(StrEnum):
    """Team API event type values recognized by adapter Team evidence readers."""

    DISPATCH_QUEUED = "dispatch_queued"
    HANDOFF_SUBMITTED = "handoff_submitted"
    HOOK_RECEIPT = "hook_receipt"
    MESSAGE_RECEIVED = "message_received"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
