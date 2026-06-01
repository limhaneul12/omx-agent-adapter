from pathlib import Path

import pytest

from omx_remote.schemas.discovery_gate_schemas import (
    DiscoveryGateDeepInterviewReference,
    DiscoveryGateNoBuildAssessment,
    DiscoveryGateResult,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateCompanyRunSuitability,
    DiscoveryGateDeepInterviewMode,
    DiscoveryGateDelegationLevel,
    DiscoveryGateProfile,
    DiscoveryGateResearchNeed,
    DiscoveryGateTaskSize,
    DiscoveryGateVerdict,
)


def _no_build_assessment(plausible: bool = False) -> DiscoveryGateNoBuildAssessment:
    return DiscoveryGateNoBuildAssessment(
        plausible=plausible,
        reasons=("Unsafe or redundant request.",) if plausible else (),
        cheaper_alternatives=("route-next",),
        roi_justification="Company-run ROI was checked before macro execution.",
    )


def _deep_interview_reference(
    mode: DiscoveryGateDeepInterviewMode = DiscoveryGateDeepInterviewMode.SKIP,
) -> DiscoveryGateDeepInterviewReference:
    return DiscoveryGateDeepInterviewReference(
        mode=mode,
        handoff_path="discovery/interview-handoff.md"
        if mode != DiscoveryGateDeepInterviewMode.SKIP
        else None,
        transcript_reference_path=None,
        question_count=None,
        readiness_gates_satisfied=(),
        unresolved_gates=("non_goals",) if mode != DiscoveryGateDeepInterviewMode.SKIP else (),
    )


def test_ready_for_company_run_requires_non_goals_and_boundaries(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-goals and decision boundaries"):
        DiscoveryGateResult(
            command_id="discovery-gate",
            objective="build a real company-run engine",
            cwd=str(tmp_path),
            profile=DiscoveryGateProfile.STANDARD,
            status="succeeded",
            verdict=DiscoveryGateVerdict.READY_FOR_COMPANY_RUN,
            ambiguity_score=0.25,
            task_size=DiscoveryGateTaskSize.ROADMAP,
            autonomy_level=DiscoveryGateDelegationLevel.FULL_DELEGATE_TO_ORCHESTRATOR,
            recommended_next_command="builtin:company-run",
            company_run_suitability=DiscoveryGateCompanyRunSuitability.HIGH,
            research_need=DiscoveryGateResearchNeed.RESEARCH_FIRST,
            no_build_assessment=_no_build_assessment(),
            settled_facts=("Objective exists.",),
            non_goals=(),
            decision_boundaries=(),
            acceptance_criteria=("Team/subagent gates are required.",),
            planning_artifact_refs=(),
            unresolved_questions=(),
            decision_options=(),
            evidence_needed=(),
            deep_interview=_deep_interview_reference(),
            artifacts=("discovery/discovery-decision-packet.json",),
            warnings=(),
            blocked_reasons=(),
            dissent_or_risk_notes=(),
        )


def test_no_build_requires_concrete_reason(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no-build verdict requires"):
        DiscoveryGateResult(
            command_id="discovery-gate",
            objective="do not build this duplicated feature",
            cwd=str(tmp_path),
            profile=DiscoveryGateProfile.QUICK,
            status="succeeded",
            verdict=DiscoveryGateVerdict.NO_BUILD,
            ambiguity_score=0.1,
            task_size=DiscoveryGateTaskSize.SMALL,
            autonomy_level=DiscoveryGateDelegationLevel.ASK_USER_FOR_MATERIAL_DECISIONS,
            recommended_next_command="no-build",
            company_run_suitability=DiscoveryGateCompanyRunSuitability.LOW,
            research_need=DiscoveryGateResearchNeed.NOT_NEEDED,
            no_build_assessment=DiscoveryGateNoBuildAssessment(
                plausible=False,
                reasons=(),
                cheaper_alternatives=("route-next",),
                roi_justification="No-build was not justified by concrete evidence.",
            ),
            settled_facts=("Objective exists.",),
            non_goals=("Do not launch Team.",),
            decision_boundaries=("Stop before implementation.",),
            acceptance_criteria=("No implementation artifacts are written.",),
            planning_artifact_refs=(),
            unresolved_questions=(),
            decision_options=(),
            evidence_needed=(),
            deep_interview=_deep_interview_reference(),
            artifacts=("discovery/discovery-decision-packet.json",),
            warnings=(),
            blocked_reasons=(),
            dissent_or_risk_notes=(),
        )


def test_deep_interview_handoff_requires_reference_path() -> None:
    with pytest.raises(ValueError, match="handoff or transcript path"):
        DiscoveryGateDeepInterviewReference(
            mode=DiscoveryGateDeepInterviewMode.HANDOFF,
            handoff_path=None,
            transcript_reference_path=None,
            question_count=None,
            readiness_gates_satisfied=(),
            unresolved_gates=("decision_boundaries",),
        )
