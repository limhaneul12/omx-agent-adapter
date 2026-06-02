from pathlib import Path

from omx_remote.schemas.company_run_gate_schemas import (
    CompanyRunDecisionReportPayload,
    CompanyRunRoiNoBuildGatePayload,
)
from omx_remote.schemas.company_run_schemas import CompanyRunExecutionRequest
from omx_remote.schemas.discovery_gate_schemas import (
    DiscoveryGateDeepInterviewReference,
    DiscoveryGateNoBuildAssessment,
    DiscoveryGateResult,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateCompanyRunSuitability,
    DiscoveryGateDeepInterviewMode,
    DiscoveryGateDelegationLevel,
    DiscoveryGateResearchNeed,
    DiscoveryGateStatus,
    DiscoveryGateTaskSize,
    DiscoveryGateVerdict,
)

_DISCOVERY_PERSPECTIVES: tuple[str, ...] = (
    "ceo/orchestrator",
    "product/pm",
    "technical/cto",
    "risk/security/critic",
)
_CHEAPER_ALTERNATIVES: tuple[str, ...] = (
    "route-next",
    "research-brief",
    "idea-to-prd",
    "implementation-kickoff",
)
_EXPECTED_COMPANY_ARTIFACTS: tuple[str, ...] = (
    "PRD",
    "test spec",
    "execution brief",
    "implementation-kickoff",
    "Team dispatch evidence",
    "review and release-readiness evidence",
)


def company_run_discovery_should_continue(verdict: DiscoveryGateVerdict) -> bool:
    """Return whether company-run may continue after Gate 0.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        bool: Whether downstream company-run phases may continue.
    """
    continuing_verdicts = {
        DiscoveryGateVerdict.READY_FOR_COMPANY_RUN,
        DiscoveryGateVerdict.RESEARCH_FIRST,
        DiscoveryGateVerdict.SKIPPED_CLEAR_ENOUGH,
    }
    should_continue = verdict in continuing_verdicts
    return should_continue


def stop_reason_from_discovery_verdict(verdict: DiscoveryGateVerdict) -> str | None:
    """Map a non-continuing discovery verdict to a stop reason.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        str | None: Stop reason when company-run should not continue.
    """
    if company_run_discovery_should_continue(verdict=verdict):
        no_stop_reason: None = None
        return no_stop_reason
    stop_reasons = {
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW: (
            "discovery-gate requires an OMX deep-interview handoff before company-run"
        ),
        DiscoveryGateVerdict.ASK_USER: (
            "discovery-gate requires a material user decision before company-run"
        ),
        DiscoveryGateVerdict.REROUTE_SMALL_TASK: (
            "discovery-gate rerouted this request to a smaller lifecycle command"
        ),
        DiscoveryGateVerdict.NO_BUILD: (
            "discovery-gate produced a no-build decision before company-run"
        ),
        DiscoveryGateVerdict.BLOCKED: "discovery-gate blocked company-run",
    }
    reason = stop_reasons.get(verdict, "discovery-gate stopped company-run")
    return reason


def recommended_next_command_for_verdict(verdict: DiscoveryGateVerdict) -> str:
    """Return the next-command recommendation for one discovery verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        str: Recommended command or handoff.
    """
    recommendations = {
        DiscoveryGateVerdict.READY_FOR_COMPANY_RUN: "builtin:company-run",
        DiscoveryGateVerdict.RESEARCH_FIRST: "builtin:research-brief",
        DiscoveryGateVerdict.SKIPPED_CLEAR_ENOUGH: "builtin:implementation-kickoff",
        DiscoveryGateVerdict.REROUTE_SMALL_TASK: "builtin:route-next",
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW: "omx deep-interview",
        DiscoveryGateVerdict.ASK_USER: "ask-user",
        DiscoveryGateVerdict.NO_BUILD: "no-build",
        DiscoveryGateVerdict.BLOCKED: "blocked",
    }
    recommendation = recommendations.get(verdict, "builtin:company-run")
    return recommendation


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
        request [CompanyRunExecutionRequest]: Company-run request.
        verdict [DiscoveryGateVerdict]: Gate verdict.
        recommended_next_command [str]: Recommended next command.
        decision_packet_path [Path]: Discovery packet artifact path.
        summary_path [Path]: Markdown summary path.
        roi_path [Path]: ROI/no-build artifact path.
        handoff_path [Path]: Deep-interview handoff path.

    Returns:
        DiscoveryGateResult: Discovery decision packet.
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
        request [CompanyRunExecutionRequest]: Company-run request.
        discovery_result [DiscoveryGateResult]: Discovery result.

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
        discovery_result [DiscoveryGateResult]: Discovery result.
        roi_path [Path]: ROI gate path.
        decision_packet_path [Path]: Discovery packet path.
        handoff_path [Path]: Deep-interview handoff path.

    Returns:
        CompanyRunDecisionReportPayload: User-facing decision report.
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


def _status_for_verdict(verdict: DiscoveryGateVerdict) -> DiscoveryGateStatus:
    """Map a discovery verdict to the packet status.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        DiscoveryGateStatus: Packet status for the verdict.
    """
    if verdict == DiscoveryGateVerdict.BLOCKED:
        status = DiscoveryGateStatus.BLOCKED
        return status
    if verdict in {
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW,
        DiscoveryGateVerdict.ASK_USER,
        DiscoveryGateVerdict.REROUTE_SMALL_TASK,
    }:
        status = DiscoveryGateStatus.REQUIRES_AGENT_ACTION
        return status
    status = DiscoveryGateStatus.SUCCEEDED
    return status


def _suitability_for_verdict(
    verdict: DiscoveryGateVerdict,
) -> DiscoveryGateCompanyRunSuitability:
    """Map a discovery verdict to company-run suitability.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        DiscoveryGateCompanyRunSuitability: Suitability assessment.
    """
    if verdict in {
        DiscoveryGateVerdict.READY_FOR_COMPANY_RUN,
        DiscoveryGateVerdict.RESEARCH_FIRST,
    }:
        suitability = DiscoveryGateCompanyRunSuitability.HIGH
        return suitability
    if verdict == DiscoveryGateVerdict.SKIPPED_CLEAR_ENOUGH:
        suitability = DiscoveryGateCompanyRunSuitability.MEDIUM
        return suitability
    if verdict == DiscoveryGateVerdict.REROUTE_SMALL_TASK:
        suitability = DiscoveryGateCompanyRunSuitability.LOW
        return suitability
    suitability = DiscoveryGateCompanyRunSuitability.BLOCKED
    return suitability


def _research_need_for_verdict(verdict: DiscoveryGateVerdict) -> DiscoveryGateResearchNeed:
    """Map a discovery verdict to the research-need label.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        DiscoveryGateResearchNeed: Research need assessment.
    """
    if verdict in {
        DiscoveryGateVerdict.READY_FOR_COMPANY_RUN,
        DiscoveryGateVerdict.RESEARCH_FIRST,
    }:
        need = DiscoveryGateResearchNeed.RESEARCH_FIRST
        return need
    need = DiscoveryGateResearchNeed.NOT_NEEDED
    return need


def _deep_interview_reference_for_verdict(
    verdict: DiscoveryGateVerdict,
    handoff_path: Path,
) -> DiscoveryGateDeepInterviewReference:
    """Build the deep-interview reference for a discovery verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.
        handoff_path [Path]: Deep-interview handoff artifact path.

    Returns:
        DiscoveryGateDeepInterviewReference: Interview handoff or skip reference.
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


def _task_size_for_verdict(verdict: DiscoveryGateVerdict) -> DiscoveryGateTaskSize:
    """Map a discovery verdict to a task-size label.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        DiscoveryGateTaskSize: Task-size classification.
    """
    if verdict == DiscoveryGateVerdict.REROUTE_SMALL_TASK:
        task_size = DiscoveryGateTaskSize.SMALL
        return task_size
    task_size = DiscoveryGateTaskSize.ROADMAP
    return task_size


def _ambiguity_score_for_verdict(verdict: DiscoveryGateVerdict) -> float:
    """Map a discovery verdict to a bounded ambiguity score.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        float: Ambiguity score from 0.0 to 1.0.
    """
    if verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW:
        ambiguity_score = 0.85
        return ambiguity_score
    if verdict in {DiscoveryGateVerdict.ASK_USER, DiscoveryGateVerdict.BLOCKED}:
        ambiguity_score = 0.75
        return ambiguity_score
    if verdict == DiscoveryGateVerdict.REROUTE_SMALL_TASK:
        ambiguity_score = 0.2
        return ambiguity_score
    ambiguity_score = 0.35
    return ambiguity_score


def _no_build_assessment_for_verdict(
    verdict: DiscoveryGateVerdict,
) -> DiscoveryGateNoBuildAssessment:
    """Build no-build and cheaper-route assessment for a verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        DiscoveryGateNoBuildAssessment: No-build assessment.
    """
    plausible = verdict == DiscoveryGateVerdict.NO_BUILD
    reasons = _no_build_reasons_for_verdict(verdict=verdict)
    assessment = DiscoveryGateNoBuildAssessment(
        plausible=plausible,
        reasons=reasons,
        cheaper_alternatives=_CHEAPER_ALTERNATIVES,
        roi_justification=_roi_justification(verdict=verdict),
    )
    return assessment


def _roi_justification(verdict: DiscoveryGateVerdict) -> str:
    """Build ROI justification text for a discovery verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        str: ROI justification.
    """
    if company_run_discovery_should_continue(verdict=verdict):
        justification = (
            "Company-run is justified by explicit objective boundaries plus required "
            "research, planning, implementation-kickoff, Team/subagent, review, and "
            "release-readiness artifacts."
        )
        return justification
    justification = (
        "Company-run is not justified until the discovery decision is resolved; "
        "a smaller command or deep-interview handoff should happen first."
    )
    return justification


def _no_build_reasons_for_verdict(
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Return concrete no-build reasons for a discovery verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: No-build reasons, when present.
    """
    if verdict == DiscoveryGateVerdict.NO_BUILD:
        reasons = ("The objective explicitly requested or implied a no-build outcome.",)
        return reasons
    if verdict == DiscoveryGateVerdict.REROUTE_SMALL_TASK:
        reasons = ("A smaller lifecycle command appears sufficient.",)
        return reasons
    empty_reasons: tuple[str, ...] = ()
    return empty_reasons


def _settled_facts_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Build settled discovery facts from the request and verdict.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Settled facts.
    """
    facts = (
        f"Objective supplied by caller: {request.objective}",
        f"Company-run discovery profile: {request.discovery_profile}",
    )
    if company_run_discovery_should_continue(verdict=verdict):
        facts = (*facts, "The objective includes enough explicit boundary signals for Gate 0.")
    return facts


def _non_goals_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Extract or synthesize non-goals for the discovery packet.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Non-goal statements.
    """
    objective = request.objective.casefold()
    if "do not" in objective or "without" in objective or "non-goal" in objective:
        non_goals = (f"Preserve stated non-goals from objective: {request.objective}",)
        return non_goals
    if verdict in {
        DiscoveryGateVerdict.REROUTE_SMALL_TASK,
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW,
        DiscoveryGateVerdict.NO_BUILD,
    }:
        non_goals = ("Do not launch Team or implementation before Gate 0 is resolved.",)
        return non_goals
    empty_non_goals: tuple[str, ...] = ()
    return empty_non_goals


def _decision_boundaries_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Extract or synthesize decision boundaries for the discovery packet.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Decision boundaries.
    """
    objective = request.objective.casefold()
    if any(marker in objective for marker in ("boundary", "boundaries", "within", "preserve")):
        boundaries = (
            f"Preserve explicit decision boundaries from objective: {request.objective}",
        )
        return boundaries
    if verdict in {
        DiscoveryGateVerdict.REROUTE_SMALL_TASK,
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW,
        DiscoveryGateVerdict.NO_BUILD,
    }:
        boundaries = ("Stop before expensive company-run work until boundaries are clear.",)
        return boundaries
    empty_boundaries: tuple[str, ...] = ()
    return empty_boundaries


def _acceptance_criteria_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Build acceptance criteria for the discovery packet.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Acceptance criteria.
    """
    if company_run_discovery_should_continue(verdict=verdict):
        criteria = (f"Produce the artifacts and evidence requested by: {request.objective}",)
        return criteria
    if verdict == DiscoveryGateVerdict.NO_BUILD:
        criteria = ("No implementation or Team launch occurs for the stopped request.",)
        return criteria
    empty_criteria: tuple[str, ...] = ()
    return empty_criteria


def _unresolved_questions_for_verdict(
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Return unresolved discovery questions implied by the verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Questions that must be resolved before proceeding.
    """
    if verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW:
        questions = (
            "What are the explicit non-goals?",
            "What decision boundaries may the orchestrator own without user input?",
        )
        return questions
    if verdict == DiscoveryGateVerdict.ASK_USER:
        questions = ("Which lifecycle route should own this request?",)
        return questions
    empty_questions: tuple[str, ...] = ()
    return empty_questions


def _decision_options_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return user-facing decision options implied by the verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Decision options.
    """
    if verdict == DiscoveryGateVerdict.ASK_USER:
        options = ("Proceed to research-brief", "Run OMX deep-interview", "Stop as no-build")
        return options
    empty_options: tuple[str, ...] = ()
    return empty_options


def _evidence_needed_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return additional evidence required by the verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Evidence requirements.
    """
    if verdict in {
        DiscoveryGateVerdict.READY_FOR_COMPANY_RUN,
        DiscoveryGateVerdict.RESEARCH_FIRST,
    }:
        evidence = ("Research council evidence before PRD and implementation kickoff.",)
        return evidence
    if verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW:
        evidence = ("OMX deep-interview transcript or handoff result.",)
        return evidence
    empty_evidence: tuple[str, ...] = ()
    return empty_evidence


def _warnings_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return warnings implied by the verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Warning messages.
    """
    if verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW:
        warnings = ("Company-run stopped before research because ambiguity remains.",)
        return warnings
    empty_warnings: tuple[str, ...] = ()
    return empty_warnings


def _blocked_reasons_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return blocked reasons implied by the verdict.

    Args:
        verdict [DiscoveryGateVerdict]: Discovery-gate verdict.

    Returns:
        tuple[str, ...]: Blocked reasons.
    """
    reason = stop_reason_from_discovery_verdict(verdict=verdict)
    blocked_reasons = (reason,) if reason is not None else ()
    return blocked_reasons


def _delegation_level_for_request(
    request: CompanyRunExecutionRequest,
) -> DiscoveryGateDelegationLevel:
    """Map request autonomy to discovery delegation level.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.

    Returns:
        DiscoveryGateDelegationLevel: Delegation level for the discovery packet.
    """
    if request.autonomy == "agent":
        level = DiscoveryGateDelegationLevel.FULL_DELEGATE_TO_ORCHESTRATOR
        return level
    level = DiscoveryGateDelegationLevel.UNSPECIFIED
    return level
