from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class CommandRoleExecution(StrEnum):
    """Execution ownership for a workflow role lane."""

    CODEX_SUBAGENT = "codex_subagent"
    OMX_TEAM = "omx_team"
    ALEXANDRIA_MEMORY = "alexandria_memory"
    LOCAL_EVIDENCE = "local_evidence"
    SYNTHESIS = "synthesis"
    VALIDATION_GATE = "validation_gate"
    RUNTIME_HANDOFF = "runtime_handoff"


class CommandRoleLane(StrictSchemaModel):
    """Named specialist lane declared by a composed command step."""

    id: NonEmptyString
    execution: CommandRoleExecution
    purpose: NonEmptyString
    artifact: NonEmptyString | None = None
    approval_required: bool = False
