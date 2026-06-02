"""Factories for discovery command payloads."""

from pathlib import Path

from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunExecutionRequest,
)
from omx_remote.schemas.company_run_gate_schemas import (
    CompanyRunDecisionReportPayload,
    CompanyRunRoiNoBuildGatePayload,
)
from omx_remote.schemas.discovery_gate_schemas import (
    DiscoveryGateDeepInterviewReference,
    DiscoveryGateResult,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateCompanyRunSuitability,
    DiscoveryGateDeepInterviewMode,
    DiscoveryGateVerdict,
)

from .discovery_payload_constants import (
    _CHEAPER_ALTERNATIVES,
    _DISCOVERY_PERSPECTIVES,
    _EXPECTED_COMPANY_ARTIFACTS,
)
from .discovery_payload_request import (
    _acceptance_criteria_for_request,
    _decision_boundaries_for_request,
    _delegation_level_for_request,
    _non_goals_for_request,
    _settled_facts_for_request,
)
from .discovery_payload_verdict import (
    _ambiguity_score_for_verdict,
    _blocked_reasons_for_verdict,
    _decision_options_for_verdict,
    _evidence_needed_for_verdict,
    _no_build_assessment_for_verdict,
    _research_need_for_verdict,
    _status_for_verdict,
    _suitability_for_verdict,
    _task_size_for_verdict,
    _unresolved_questions_for_verdict,
    _warnings_for_verdict,
    company_run_discovery_should_continue,
)


def build_discovery_result(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
    recommended_next_command: str,
    decision_packet_path: Path,
    summary_path: Path,
    roi_path: Path,
    handoff_path: Path,
) -> DiscoveryGateResult:
    """Build the typed DiscoveryGateResult decision packet.

    Args:
        request: Company-run execution request data.
        verdict: Discovery verdict selected for this request.
        recommended_next_command: Suggested next command from the verdict mapping.
        decision_packet_path: Path to write the decision packet artifact.
        summary_path: Path to write the markdown summary artifact.
        roi_path: Path to write the ROI/no-build gate artifact.
        handoff_path: Path to write deep-interview handoff details.

    Returns:
        DiscoveryGateResult: Discovery gate packet payload.
    """
    result = DiscoveryGateResult(
        command_id="discovery-gate",
        objective=request.objective,
        cwd=request.cwd,
        profile=request.discovery_profile,
        status=_status_for_verdict(verdict=verdict),
        verdict=verdict,
        ambiguity_score=_ambiguity_score_for_verdict(verdict=verdict),
        task_size=_task_size_for_verdict(verdict=verdict),
        autonomy_level=_delegation_level_for_request(request=request),
        recommended_next_command=recommended_next_command,
        company_run_suitability=_suitability_for_verdict(verdict=verdict),
        research_need=_research_need_for_verdict(verdict=verdict),
        no_build_assessment=_no_build_assessment_for_verdict(verdict=verdict),
        settled_facts=_settled_facts_for_request(request=request, verdict=verdict),
        non_goals=_non_goals_for_request(request=request, verdict=verdict),
        decision_boundaries=_decision_boundaries_for_request(
            request=request,
            verdict=verdict,
        ),
        acceptance_criteria=_acceptance_criteria_for_request(
            request=request,
            verdict=verdict,
        ),
        planning_artifact_refs=(),
        unresolved_questions=_unresolved_questions_for_verdict(verdict=verdict),
        decision_options=_decision_options_for_verdict(verdict=verdict),
        evidence_needed=_evidence_needed_for_verdict(verdict=verdict),
        deep_interview=_deep_interview_reference_for_verdict(
            verdict=verdict,
            handoff_path=handoff_path,
        ),
        artifacts=(
            str(decision_packet_path),
            str(summary_path),
            str(roi_path),
            str(handoff_path),
        ),
        warnings=_warnings_for_verdict(verdict=verdict),
        blocked_reasons=_blocked_reasons_for_verdict(verdict=verdict),
        dissent_or_risk_notes=(
            "Internal Gate 0 perspectives are recorded without user-facing vote theater.",
        ),
    )
    return result


def build_roi_payload(
    request: CompanyRunExecutionRequest,
    discovery_result: DiscoveryGateResult,
) -> CompanyRunRoiNoBuildGatePayload:
    """Build the ROI/no-build gate payload.

    Args:
        request: Company-run execution request metadata.
        discovery_result: Discovery verdict result to transform into ROI payload.

    Returns:
        CompanyRunRoiNoBuildGatePayload: ROI/no-build payload.
    """
    payload = CompanyRunRoiNoBuildGatePayload(
        suitability=DiscoveryGateCompanyRunSuitability(
            discovery_result.company_run_suitability
        ),
        final_verdict=DiscoveryGateVerdict(discovery_result.verdict),
        cheaper_alternatives_considered=_CHEAPER_ALTERNATIVES,
        no_build_reasons_considered=discovery_result.no_build_assessment.reasons,
        expected_artifacts_if_proceeding=_EXPECTED_COMPANY_ARTIFACTS,
        expected_team_worker_count=request.worker_count,
        token_time_risk="high-cost macro path; allowed only when Gate 0 is justified",
        decision_owner="company_orchestrator",
        rationale=discovery_result.no_build_assessment.roi_justification,
        perspectives_recorded=_DISCOVERY_PERSPECTIVES,
    )
    return payload


def build_decision_report_payload(
    discovery_result: DiscoveryGateResult,
    roi_path: Path,
    decision_packet_path: Path,
    handoff_path: Path,
) -> CompanyRunDecisionReportPayload:
    """Build the user-facing decision report payload.

    Args:
        discovery_result: Discovery gate result payload.
        roi_path: Path to the ROI/no-build gate artifact.
        decision_packet_path: Path to the discovery decision packet artifact.
        handoff_path: Path to the deep-interview handoff artifact.

    Returns:
        CompanyRunDecisionReportPayload: User-facing decision report payload.
    """
    verdict = DiscoveryGateVerdict(discovery_result.verdict)
    should_continue = company_run_discovery_should_continue(verdict=verdict)
    next_action = (
        "Continue into route-next, research, planning, implementation-kickoff, and Team gates."
        if should_continue
        else f"Stop company-run and follow {discovery_result.recommended_next_command}."
    )
    payload = CompanyRunDecisionReportPayload(
        decision=str(discovery_result.verdict),
        rationale=(
            discovery_result.no_build_assessment.roi_justification,
            "Internal perspectives were recorded; raw ballots remain audit-only.",
        ),
        concerns=(
            "Company-run is expensive and must not be used for tiny tasks.",
            "Deep-interview is required when non-goals or decision boundaries remain unclear.",
        ),
        next_actions=(next_action,),
        user_visible_status="discovery",
        artifact_paths=(
            str(decision_packet_path),
            str(roi_path),
            str(handoff_path),
        ),
        governance_artifact_paths=(str(decision_packet_path), str(roi_path)),
        audit_details_available=True,
    )
    return payload


def _deep_interview_reference_for_verdict(
    verdict: DiscoveryGateVerdict,
    handoff_path: Path,
) -> DiscoveryGateDeepInterviewReference:
    """Build the deep-interview reference for a discovery verdict.

    Args:
        verdict: Discovery verdict driving interview mode.
        handoff_path: Deep-interview handoff path if required.

    Returns:
        DiscoveryGateDeepInterviewReference: Deep-interview reference payload.
    """
    mode = (
        DiscoveryGateDeepInterviewMode.HANDOFF
        if verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW
        else DiscoveryGateDeepInterviewMode.SKIP
    )
    reference = DiscoveryGateDeepInterviewReference(
        mode=mode,
        handoff_path=str(handoff_path) if mode == DiscoveryGateDeepInterviewMode.HANDOFF else None,
        transcript_reference_path=None,
        question_count=None,
        readiness_gates_satisfied=(),
        unresolved_gates=(
            ("non_goals", "decision_boundaries")
            if mode == DiscoveryGateDeepInterviewMode.HANDOFF
            else ()
        ),
    )
    return reference
