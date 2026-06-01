from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.preflight_enums import (
    PreflightCategory,
    PreflightReportStatus,
    PreflightSeverity,
)


class PreflightCheckResult(StrictSchemaModel):
    """Represents one reusable preflight check result."""

    category: PreflightCategory
    severity: PreflightSeverity
    summary: NonEmptyString
    detail: NonEmptyString
    blocks_execution: bool
    evidence: NonEmptyString | None = None


class PreflightReport(StrictSchemaModel):
    """Represents an aggregate preflight report."""

    status: PreflightReportStatus
    checks: tuple[PreflightCheckResult, ...]
    blockers: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()
    command_id: NonEmptyString | None = None
    qualified_id: NonEmptyString | None = None
    route: NonEmptyString | None = None
