from pathlib import Path

from omx_remote.runtime.company_run.company_run_artifacts import (
    write_company_json,
    write_company_markdown,
)
from omx_remote.runtime.company_run.company_run_discovery_payloads import (
    build_decision_report_payload,
    build_discovery_result,
    build_roi_payload,
    company_run_discovery_should_continue,
    recommended_next_command_for_verdict,
    stop_reason_from_discovery_verdict,
)
from omx_remote.runtime.company_run.company_run_phase_texts import (
    deep_interview_handoff_markdown,
    discovery_summary_markdown,
    user_facing_decision_report_markdown,
)
from omx_remote.schemas.company_run_gate_schemas import CompanyRunDiscoveryArtifacts
from omx_remote.schemas.company_run_schemas import CompanyRunExecutionRequest
from omx_remote.shared.omx_enums.discovery_gate_enums import DiscoveryGateVerdict

_SMALL_TASK_MARKERS: tuple[str, ...] = (
    "status only",
    "just status",
    "just lint",
    "just format",
    "tiny task",
    "small deterministic",
    "fix a typo",
    "typo only",
)
_DEEP_INTERVIEW_MARKERS: tuple[str, ...] = (
    "vague",
    "unclear",
    "ambiguous",
    "don't assume",
    "dont assume",
    "모호",
    "애매",
)
_NO_BUILD_MARKERS: tuple[str, ...] = (
    "no-build",
    "no build",
    "do not build",
    "don't build",
    "dont build",
)
_RESEARCH_FIRST_MARKERS: tuple[str, ...] = (
    "research first",
    "investigate whether",
    "evaluate whether",
    "compare options",
    "feasibility",
)
_NON_GOAL_MARKERS: tuple[str, ...] = (
    "non-goal",
    "non goal",
    "do not",
    "don't",
    "dont",
    "without",
)
_DECISION_BOUNDARY_MARKERS: tuple[str, ...] = (
    "boundary",
    "boundaries",
    "within",
    "preserve",
    "autonomy",
)
_OUTCOME_MARKERS: tuple[str, ...] = (
    "prd",
    "test",
    "implementation",
    "team",
    "review",
    "release",
    "artifact",
    "evidence",
)


def write_company_run_discovery_artifacts(
    company_root: Path,
    request: CompanyRunExecutionRequest,
) -> CompanyRunDiscoveryArtifacts:
    """Write company-run Gate 0 discovery, ROI, and decision-report artifacts.

    Args:
        company_root [Path]: Company-run artifact root.
        request [CompanyRunExecutionRequest]: Company-run execution request.

    Returns:
        CompanyRunDiscoveryArtifacts: Typed paths and decision result.
    """
    discovery_dir = company_root / "discovery"
    decisions_dir = company_root / "decisions"
    decision_packet_path = discovery_dir / "discovery-decision-packet.json"
    summary_path = discovery_dir / "discovery-summary.md"
    roi_path = discovery_dir / "roi-no-build-gate.json"
    handoff_path = discovery_dir / "deep-interview-handoff.md"
    decision_report_json_path = decisions_dir / "discovery-decision-report.json"
    decision_report_markdown_path = decisions_dir / "discovery-decision-report.md"

    verdict = _verdict_for_request(request=request)
    recommended_next_command = recommended_next_command_for_verdict(verdict=verdict)
    discovery_result = build_discovery_result(
        request=request,
        verdict=verdict,
        recommended_next_command=recommended_next_command,
        decision_packet_path=decision_packet_path,
        summary_path=summary_path,
        roi_path=roi_path,
        handoff_path=handoff_path,
    )
    roi_payload = build_roi_payload(
        request=request,
        discovery_result=discovery_result,
    )
    decision_report_payload = build_decision_report_payload(
        discovery_result=discovery_result,
        roi_path=roi_path,
        decision_packet_path=decision_packet_path,
        handoff_path=handoff_path,
    )
    invocation = _deep_interview_invocation(request=request)

    write_company_json(path=decision_packet_path, payload=discovery_result)
    write_company_markdown(
        path=summary_path,
        text=discovery_summary_markdown(
            objective=request.objective,
            verdict=verdict.value,
            recommended_next_command=recommended_next_command,
        ),
    )
    write_company_json(path=roi_path, payload=roi_payload)
    write_company_markdown(
        path=handoff_path,
        text=deep_interview_handoff_markdown(
            objective=request.objective,
            invocation=invocation,
        ),
    )
    write_company_json(path=decision_report_json_path, payload=decision_report_payload)
    write_company_markdown(
        path=decision_report_markdown_path,
        text=user_facing_decision_report_markdown(
            decision=decision_report_payload.decision,
            rationale=decision_report_payload.rationale,
            concerns=decision_report_payload.concerns,
            next_actions=decision_report_payload.next_actions,
            artifact_paths=decision_report_payload.artifact_paths,
        ),
    )

    stop_reason = stop_reason_from_discovery_verdict(verdict=verdict)
    artifacts = CompanyRunDiscoveryArtifacts(
        verdict=verdict,
        should_continue=company_run_discovery_should_continue(verdict=verdict),
        discovery_decision_packet_path=str(decision_packet_path),
        discovery_summary_path=str(summary_path),
        roi_no_build_gate_path=str(roi_path),
        deep_interview_handoff_path=str(handoff_path),
        decision_report_json_path=str(decision_report_json_path),
        decision_report_markdown_path=str(decision_report_markdown_path),
        stop_reason=stop_reason,
    )
    return artifacts


def _verdict_for_request(request: CompanyRunExecutionRequest) -> DiscoveryGateVerdict:
    """Classify the deterministic first Gate 0 verdict for company-run.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.

    Returns:
        DiscoveryGateVerdict: Gate 0 verdict.
    """
    objective = request.objective.casefold()
    if _contains_marker(text=objective, markers=_NO_BUILD_MARKERS):
        verdict = DiscoveryGateVerdict.NO_BUILD
        return verdict
    if _contains_marker(text=objective, markers=_SMALL_TASK_MARKERS):
        verdict = DiscoveryGateVerdict.REROUTE_SMALL_TASK
        return verdict
    if _contains_marker(text=objective, markers=_DEEP_INTERVIEW_MARKERS):
        verdict = DiscoveryGateVerdict.RUN_DEEP_INTERVIEW
        return verdict
    if _contains_marker(text=objective, markers=_RESEARCH_FIRST_MARKERS):
        verdict = DiscoveryGateVerdict.RESEARCH_FIRST
        return verdict
    if not _has_company_run_readiness_signals(objective=objective):
        verdict = DiscoveryGateVerdict.RUN_DEEP_INTERVIEW
        return verdict
    verdict = DiscoveryGateVerdict.READY_FOR_COMPANY_RUN
    return verdict


def _contains_marker(text: str, markers: tuple[str, ...]) -> bool:
    """Return whether one marker appears in text.

    Args:
        text [str]: Lower-cased text to inspect.
        markers [tuple[str, ...]]: Marker phrases.

    Returns:
        bool: Whether a marker matched.
    """
    matched = any(marker in text for marker in markers)
    return matched


def _has_company_run_readiness_signals(objective: str) -> bool:
    """Return whether objective has explicit Gate 0 readiness signals.

    Args:
        objective [str]: Lower-cased objective.

    Returns:
        bool: Whether company-run may proceed without deep-interview.
    """
    has_non_goal = _contains_marker(text=objective, markers=_NON_GOAL_MARKERS)
    has_boundary = _contains_marker(
        text=objective,
        markers=_DECISION_BOUNDARY_MARKERS,
    )
    has_outcome = _contains_marker(text=objective, markers=_OUTCOME_MARKERS)
    is_ready = has_non_goal and has_boundary and has_outcome
    return is_ready


def _deep_interview_invocation(request: CompanyRunExecutionRequest) -> str:
    """Build the concrete OMX deep-interview handoff command.

    Args:
        request [CompanyRunExecutionRequest]: Company-run execution request.

    Returns:
        str: Suggested command invocation.
    """
    profile = str(request.discovery_profile)
    invocation = f'omx deep-interview --{profile} "{request.objective}"'
    return invocation
