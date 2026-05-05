from enum import StrEnum


class ManagedFlowKind(StrEnum):
    """Flow kinds projected into the multi-operator control snapshot."""

    RALPH = "ralph"
    TEAM = "team"


class ManagedInterventionAction(StrEnum):
    """Intervention actions that can be suggested for managed OMX flows."""

    LAUNCH = "launch"
    RESUME = "resume"
    RETRY = "retry"
    CLEANUP = "cleanup"
    CANCEL = "cancel"
    ESCALATE = "escalate"
