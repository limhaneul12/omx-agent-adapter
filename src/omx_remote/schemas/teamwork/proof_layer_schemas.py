from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class TeamProofLayerName(StrEnum):
    """Stable proof-layer names for Team launch/status evidence."""

    PRD_DAG_IMPORT = "prd_dag_import"
    ASSIGNMENT = "assignment"
    WORKER_READINESS = "worker_readiness"
    DISPATCH = "dispatch"
    COMPLETION = "completion"


class TeamProofLayerState(StrEnum):
    """Machine-readable state for one Team proof layer."""

    MISSING = "missing"
    PARTIAL = "partial"
    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class TeamProofLayerSummary(StrictSchemaModel):
    """Summarizes one evidence layer in a Team/Ralph execution wave."""

    name: TeamProofLayerName
    state: TeamProofLayerState
    summary: NonEmptyString
    source_names: tuple[NonEmptyString, ...] = ()
    blocking: bool
