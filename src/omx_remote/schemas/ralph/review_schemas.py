from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
)
from omx_remote.shared.omx_enums.ralph_enums import RalphPostTeamReviewDecision


class RalphPostTeamReviewRequest(StrictSchemaModel):
    """Ralph-owned request to review Team Admin aggregation against the PRD."""

    ralph_prd_artifact: RalphPrdArtifact
    aggregation_report: TeamAdminAggregationReport


class RalphPostTeamReviewResult(StrictSchemaModel):
    """Goal-facing result produced by Ralph after reviewing Team output."""

    decision: RalphPostTeamReviewDecision
    complete: bool
    follow_up_required: bool
    human_review_required: bool
    merge_approved: bool
    completed_workers: NonEmptyStrings
    follow_up_workers: NonEmptyStrings
    startup_issue_workers: NonEmptyStrings = ()
    review_blockers: NonEmptyStrings
    summary: NonEmptyString
