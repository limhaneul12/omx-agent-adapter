from pydantic import Field

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateCompanyRunSuitability,
    DiscoveryGateVerdict,
)


class CompanyRunRoiNoBuildGatePayload(StrictSchemaModel):
    """Typed company-run ROI/no-build gate contract."""

    suitability: DiscoveryGateCompanyRunSuitability
    final_verdict: DiscoveryGateVerdict
    cheaper_alternatives_considered: tuple[NonEmptyString, ...]
    no_build_reasons_considered: tuple[NonEmptyString, ...]
    expected_artifacts_if_proceeding: tuple[NonEmptyString, ...]
    expected_team_worker_count: int = Field(ge=3)
    token_time_risk: NonEmptyString
    decision_owner: NonEmptyString
    rationale: NonEmptyString
    perspectives_recorded: tuple[NonEmptyString, ...]


class CompanyRunDecisionReportPayload(StrictSchemaModel):
    """User-facing decision report summary without raw vote ceremony."""

    decision: NonEmptyString
    rationale: tuple[NonEmptyString, ...]
    concerns: tuple[NonEmptyString, ...]
    next_actions: tuple[NonEmptyString, ...]
    user_visible_status: NonEmptyString
    artifact_paths: tuple[NonEmptyString, ...]
    governance_artifact_paths: tuple[NonEmptyString, ...]
    audit_details_available: bool


class CompanyRunDiscoveryArtifacts(StrictSchemaModel):
    """Paths written by the company-run discovery gate."""

    verdict: DiscoveryGateVerdict
    should_continue: bool
    discovery_decision_packet_path: NonEmptyString
    discovery_summary_path: NonEmptyString
    roi_no_build_gate_path: NonEmptyString
    deep_interview_handoff_path: NonEmptyString
    decision_report_json_path: NonEmptyString
    decision_report_markdown_path: NonEmptyString
    stop_reason: NonEmptyString | None
