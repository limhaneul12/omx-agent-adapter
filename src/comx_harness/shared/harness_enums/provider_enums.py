from enum import StrEnum


class ProviderId(StrEnum):
    CODEX = "codex"
    OMX = "omx"


class Operation(StrEnum):
    CAPABILITIES = "capabilities"
    PLAN = "plan"
    RUN = "run"
    HANDOFF = "handoff"
    STATUS = "status"
    EVENTS = "events"
    CANCEL = "cancel"
    RESUME = "resume"
    ARTIFACTS = "artifacts"
