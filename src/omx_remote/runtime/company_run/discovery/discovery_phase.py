from enum import StrEnum
from pathlib import Path

from omx_remote.runtime.company_run.artifacts.artifact_writers import (
    write_company_json,
    write_company_markdown,
)
from omx_remote.runtime.company_run.discovery.discovery_payload_builders import (
    build_decision_report_payload,
    build_discovery_result,
    build_roi_payload,
)
from omx_remote.runtime.company_run.discovery.discovery_payload_verdict import (
    company_run_discovery_should_continue,
    recommended_next_command_for_verdict,
    stop_reason_from_discovery_verdict,
)
from omx_remote.runtime.company_run.phases.phase_texts import (
    deep_interview_handoff_markdown,
    discovery_summary_markdown,
    user_facing_decision_report_markdown,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunExecutionRequest,
)
from omx_remote.schemas.company_run_gate_schemas import CompanyRunDiscoveryArtifacts
from omx_remote.shared.omx_enums.company_run_discovery_enums import (
    COMPANY_RUN_DECISION_BOUNDARY_MARKERS,
    COMPANY_RUN_DEEP_INTERVIEW_MARKERS,
    COMPANY_RUN_NON_GOAL_MARKERS,
    COMPANY_RUN_OUTCOME_MARKERS,
    COMPANY_RUN_RESEARCH_FIRST_MARKERS,
    COMPANY_RUN_SMALL_TASK_MARKERS,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import DiscoveryGateVerdict


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
    if _contains_no_build_intent(objective=objective):
        verdict = DiscoveryGateVerdict.NO_BUILD
        return verdict
    if _contains_marker(text=objective, markers=COMPANY_RUN_SMALL_TASK_MARKERS):
        verdict = DiscoveryGateVerdict.REROUTE_SMALL_TASK
        return verdict
    if _contains_marker(text=objective, markers=COMPANY_RUN_DEEP_INTERVIEW_MARKERS):
        verdict = DiscoveryGateVerdict.RUN_DEEP_INTERVIEW
        return verdict
    if _contains_marker(text=objective, markers=COMPANY_RUN_RESEARCH_FIRST_MARKERS):
        verdict = DiscoveryGateVerdict.RESEARCH_FIRST
        return verdict
    if not _has_company_run_readiness_signals(objective=objective):
        verdict = DiscoveryGateVerdict.RUN_DEEP_INTERVIEW
        return verdict
    verdict = DiscoveryGateVerdict.READY_FOR_COMPANY_RUN
    return verdict


def _contains_no_build_intent(objective: str) -> bool:
    """Return whether objective asks to stop as no-build.

    Args:
        objective [str]: Lower-cased objective text.

    Returns:
        bool: Whether the no-build marker is an instruction rather than a gate
        or risk topic being discussed.
    """
    stripped_objective = objective.strip()
    no_build_prefix_phrases = ("no-build", "no build")
    explicit_instruction_phrases = (
        "do not build",
        "don't build",
        "dont build",
        "stop as no-build",
        "stop as no build",
    )
    if stripped_objective in (*no_build_prefix_phrases, *explicit_instruction_phrases):
        return True
    if stripped_objective.startswith(
        tuple(f"{phrase} " for phrase in no_build_prefix_phrases)
    ):
        return True
    if stripped_objective.startswith(
        tuple(f"{phrase} " for phrase in explicit_instruction_phrases)
    ):
        return True
    return any(
        f" {phrase}" in stripped_objective
        for phrase in explicit_instruction_phrases
    )


def _contains_marker(
    text: str,
    markers: tuple[StrEnum, ...],
) -> bool:
    """Return whether one marker appears in text.

    Args:
        text [str]: Lower-cased text to inspect.
        markers [tuple[StrEnum, ...]]: Marker phrases.

    Returns:
        bool: Whether a marker matched.
    """
    matched = any(marker.value in text for marker in markers)
    return matched


def _has_company_run_readiness_signals(objective: str) -> bool:
    """Return whether objective has explicit Gate 0 readiness signals.

    Args:
        objective [str]: Lower-cased objective.

    Returns:
        bool: Whether company-run may proceed without deep-interview.
    """
    has_non_goal = _contains_marker(
        text=objective,
        markers=COMPANY_RUN_NON_GOAL_MARKERS,
    )
    has_boundary = _contains_marker(
        text=objective,
        markers=COMPANY_RUN_DECISION_BOUNDARY_MARKERS,
    )
    has_outcome = _contains_marker(
        text=objective,
        markers=COMPANY_RUN_OUTCOME_MARKERS,
    )
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
