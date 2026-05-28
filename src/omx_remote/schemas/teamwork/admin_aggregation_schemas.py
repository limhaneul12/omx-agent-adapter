from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    NonEmptyStrings,
    StrictSchemaModel,
)
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.teamwork.proof_layer_schemas import TeamProofLayerSummary
from omx_remote.shared.omx_enums.team_admin_enums import TeamAdminAggregationState


class TeamAdminAggregationReportRequest(StrictSchemaModel):
    """Agent-facing request to collect a Team Admin aggregation report from OMX."""

    team_name: NonEmptyString
    ralph_prd_artifact: RalphPrdArtifact


class TeamAdminAggregationReport(StrictSchemaModel):
    """Ralph-facing Team Admin final aggregation report."""

    admin_id: NonEmptyString
    aggregation_state: TeamAdminAggregationState
    merge_ready: bool
    final_report_required: bool
    completed_workers: NonEmptyStrings
    missing_workers: NonEmptyStrings
    blocked_workers: NonEmptyStrings
    startup_issue_workers: NonEmptyStrings = ()
    incomplete_workers: NonEmptyStrings
    requires_human_review: bool
    requires_llm_review: bool
    task_count: int
    event_count: int
    summary: NonEmptyString
    proof_layers: tuple[TeamProofLayerSummary, ...] = ()
