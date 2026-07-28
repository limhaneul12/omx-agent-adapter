from enum import StrEnum


class SandboxMode(StrEnum):
    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    DANGER_FULL_ACCESS = "danger-full-access"


class ApprovalPolicy(StrEnum):
    UNTRUSTED = "untrusted"
    ON_REQUEST = "on-request"
    NEVER = "never"


class ReasoningEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
