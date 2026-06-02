"""Verdict-level mapping for company-run discovery artifacts."""

from omx_remote.schemas.discovery_gate_schemas import DiscoveryGateNoBuildAssessment
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateCompanyRunSuitability,
    DiscoveryGateResearchNeed,
    DiscoveryGateStatus,
    DiscoveryGateTaskSize,
    DiscoveryGateVerdict,
)

from .discovery_payload_constants import _CHEAPER_ALTERNATIVES


def company_run_discovery_should_continue(verdict: DiscoveryGateVerdict) -> bool:
    """Return whether company-run may continue after Gate 0.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        bool: ``True`` when downstream company-run phases may continue.
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
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        str | None: Human-readable stop reason, or ``None`` if continuing.
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
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        str: Suggested command or handoff target.
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


def _status_for_verdict(verdict: DiscoveryGateVerdict) -> DiscoveryGateStatus:
    """Map a discovery verdict to the packet status.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        DiscoveryGateStatus: Packet status for the discovery verdict.
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
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        DiscoveryGateCompanyRunSuitability: Suitability label for company-run.
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
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        DiscoveryGateResearchNeed: Research need level.
    """
    if verdict in {
        DiscoveryGateVerdict.READY_FOR_COMPANY_RUN,
        DiscoveryGateVerdict.RESEARCH_FIRST,
    }:
        need = DiscoveryGateResearchNeed.RESEARCH_FIRST
        return need
    need = DiscoveryGateResearchNeed.NOT_NEEDED
    return need


def _task_size_for_verdict(verdict: DiscoveryGateVerdict) -> DiscoveryGateTaskSize:
    """Map a discovery verdict to a task-size label.

    Args:
        verdict: Discovery verdict produced by Gate 0.

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
        verdict: Discovery verdict produced by Gate 0.

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


def _no_build_reasons_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return concrete no-build reasons for a discovery verdict.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        tuple[str, ...]: Reasons explaining no-build readiness.
    """
    if verdict == DiscoveryGateVerdict.NO_BUILD:
        reasons = ("The objective explicitly requested or implied a no-build outcome.",)
        return reasons
    if verdict == DiscoveryGateVerdict.REROUTE_SMALL_TASK:
        reasons = ("A smaller lifecycle command appears sufficient.",)
        return reasons
    empty_reasons: tuple[str, ...] = ()
    return empty_reasons


def _roi_justification(verdict: DiscoveryGateVerdict) -> str:
    """Build ROI justification text for a discovery verdict.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        str: ROI justification text.
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


def _unresolved_questions_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return unresolved discovery questions implied by the verdict.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        tuple[str, ...]: Questions still open after verdict assignment.
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
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        tuple[str, ...]: Human-oriented options to continue.
    """
    if verdict == DiscoveryGateVerdict.ASK_USER:
        options = ("Proceed to research-brief", "Run OMX deep-interview", "Stop as no-build")
        return options
    empty_options: tuple[str, ...] = ()
    return empty_options


def _evidence_needed_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return additional evidence required by the verdict.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        tuple[str, ...]: Evidence checkpoints required before progression.
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
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        tuple[str, ...]: Relevant warnings for the decision context.
    """
    if verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW:
        warnings = ("Company-run stopped before research because ambiguity remains.",)
        return warnings
    empty_warnings: tuple[str, ...] = ()
    return empty_warnings


def _blocked_reasons_for_verdict(verdict: DiscoveryGateVerdict) -> tuple[str, ...]:
    """Return blocked reasons implied by the verdict.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        tuple[str, ...]: Blocked reasons derived from the verdict.
    """
    reason = stop_reason_from_discovery_verdict(verdict=verdict)
    blocked_reasons = (reason,) if reason is not None else ()
    return blocked_reasons


def _no_build_assessment_for_verdict(
    verdict: DiscoveryGateVerdict,
) -> DiscoveryGateNoBuildAssessment:
    """Build no-build and cheaper-route assessment for a verdict.

    Args:
        verdict: Discovery verdict produced by Gate 0.

    Returns:
        DiscoveryGateNoBuildAssessment: Assessment payload for no-build decisions.
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
