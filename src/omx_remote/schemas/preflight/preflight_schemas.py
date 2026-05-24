from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class PreflightSeverity(StrEnum):
    """Severity for one preflight check."""

    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class PreflightReportStatus(StrEnum):
    """Aggregate preflight report status."""

    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"


class PreflightCategory(StrEnum):
    """Reusable preflight check categories."""

    GIT_STATE = "git_state"
    RUNTIME_STATE = "runtime_state"
    TOOL_AVAILABILITY = "tool_availability"
    CAPABILITY_SUPPORT = "capability_support"
    CONFIG_VALIDITY = "config_validity"
    PROMPT_FILE_VISIBILITY = "prompt_file_visibility"
    WORKTREE_VISIBILITY = "worktree_visibility"
    INTERACTIVE_REQUIREMENT = "interactive_requirement"
    LONG_RUNNING_PROCESS = "long_running_process"
    APPROVAL_REQUIREMENT = "approval_requirement"


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
