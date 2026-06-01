from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateCompanyRunSuitability,
    DiscoveryGateDeepInterviewMode,
    DiscoveryGateDelegationLevel,
    DiscoveryGateProfile,
    DiscoveryGateResearchNeed,
    DiscoveryGateStatus,
    DiscoveryGateTaskSize,
    DiscoveryGateVerdict,
)


class DiscoveryGateDeepInterviewReference(StrictSchemaModel):
    """Concrete OMX deep-interview handoff/import evidence."""

    mode: DiscoveryGateDeepInterviewMode
    handoff_path: NonEmptyString | None
    transcript_reference_path: NonEmptyString | None
    question_count: int | None = Field(ge=0)
    readiness_gates_satisfied: tuple[NonEmptyString, ...]
    unresolved_gates: tuple[NonEmptyString, ...]

    @model_validator(mode="after")
    def _validate_reference_paths(self) -> "DiscoveryGateDeepInterviewReference":
        """Ensure non-skip interview modes include a handoff or transcript reference.

        Returns:
            DiscoveryGateDeepInterviewReference: Validated interview reference.
        """
        if self.mode == DiscoveryGateDeepInterviewMode.SKIP:
            return self
        if self.handoff_path is None and self.transcript_reference_path is None:
            raise ValueError(
                "non-skip deep-interview references require a handoff or transcript path"
            )
        return self


class DiscoveryGateNoBuildAssessment(StrictSchemaModel):
    """No-build and cheaper-route reasoning captured before expensive workflows."""

    plausible: bool
    reasons: tuple[NonEmptyString, ...]
    cheaper_alternatives: tuple[NonEmptyString, ...]
    roi_justification: NonEmptyString

    @model_validator(mode="after")
    def _validate_no_build_reasons(self) -> "DiscoveryGateNoBuildAssessment":
        """Require concrete reasons when no-build is plausible.

        Returns:
            DiscoveryGateNoBuildAssessment: Validated assessment.
        """
        if self.plausible and not self.reasons:
            raise ValueError("plausible no-build requires at least one concrete reason")
        return self


class DiscoveryGateResult(StrictSchemaModel):
    """Stable discovery-gate decision packet contract."""

    command_id: NonEmptyString
    objective: NonEmptyString
    cwd: NonEmptyString
    profile: DiscoveryGateProfile
    status: DiscoveryGateStatus
    verdict: DiscoveryGateVerdict
    ambiguity_score: float = Field(ge=0.0, le=1.0)
    task_size: DiscoveryGateTaskSize
    autonomy_level: DiscoveryGateDelegationLevel
    recommended_next_command: NonEmptyString
    company_run_suitability: DiscoveryGateCompanyRunSuitability
    research_need: DiscoveryGateResearchNeed
    no_build_assessment: DiscoveryGateNoBuildAssessment
    settled_facts: tuple[NonEmptyString, ...]
    non_goals: tuple[NonEmptyString, ...]
    decision_boundaries: tuple[NonEmptyString, ...]
    acceptance_criteria: tuple[NonEmptyString, ...]
    planning_artifact_refs: tuple[NonEmptyString, ...]
    unresolved_questions: tuple[NonEmptyString, ...]
    decision_options: tuple[NonEmptyString, ...]
    evidence_needed: tuple[NonEmptyString, ...]
    deep_interview: DiscoveryGateDeepInterviewReference
    artifacts: tuple[NonEmptyString, ...]
    warnings: tuple[NonEmptyString, ...]
    blocked_reasons: tuple[NonEmptyString, ...]
    dissent_or_risk_notes: tuple[NonEmptyString, ...]

    @model_validator(mode="after")
    def _validate_verdict_requirements(self) -> "DiscoveryGateResult":
        """Validate artifact and routing requirements implied by the verdict.

        Returns:
            DiscoveryGateResult: Validated result.
        """
        if self.verdict == DiscoveryGateVerdict.READY_FOR_COMPANY_RUN:
            if not self.non_goals or not self.decision_boundaries:
                raise ValueError(
                    "ready-for-company-run requires non-goals and decision boundaries"
                )
            if not self.acceptance_criteria:
                raise ValueError("ready-for-company-run requires acceptance criteria")
            if not self.no_build_assessment.cheaper_alternatives:
                raise ValueError(
                    "ready-for-company-run requires cheaper alternatives considered"
                )
            if self.company_run_suitability not in {
                DiscoveryGateCompanyRunSuitability.HIGH,
                DiscoveryGateCompanyRunSuitability.MEDIUM,
            }:
                raise ValueError(
                    "ready-for-company-run requires high or medium suitability"
                )
        if self.verdict == DiscoveryGateVerdict.READY_FOR_PRD and not (
            self.acceptance_criteria and self.non_goals and self.decision_boundaries
        ):
            raise ValueError(
                "ready-for-prd requires acceptance criteria, non-goals, and decision boundaries"
            )
        if self.verdict == DiscoveryGateVerdict.READY_FOR_IMPLEMENTATION_KICKOFF:
            refs_text = " ".join(self.planning_artifact_refs).casefold()
            if not all(term in refs_text for term in ("prd", "test", "execution")):
                raise ValueError(
                    "ready-for-implementation-kickoff requires PRD, test spec, and execution brief references"
                )
        if (
            self.verdict == DiscoveryGateVerdict.RUN_DEEP_INTERVIEW
            and self.status != DiscoveryGateStatus.REQUIRES_AGENT_ACTION
            and self.deep_interview.mode != DiscoveryGateDeepInterviewMode.MANAGED_INTERVIEW
        ):
            raise ValueError(
                "run-deep-interview requires requires_agent_action unless managed interview completed"
            )
        if self.verdict == DiscoveryGateVerdict.NO_BUILD and not (
            self.no_build_assessment.plausible and self.no_build_assessment.reasons
        ):
            raise ValueError("no-build verdict requires concrete no-build reasons")
        if self.verdict == DiscoveryGateVerdict.ASK_USER and not (
            self.unresolved_questions and self.decision_options
        ):
            raise ValueError(
                "ask-user verdict requires concise unresolved questions and decision options"
            )
        if (
            self.verdict == DiscoveryGateVerdict.REROUTE_SMALL_TASK
            and self.recommended_next_command == "builtin:company-run"
        ):
            raise ValueError("reroute-small-task must not recommend company-run")
        if self.verdict == DiscoveryGateVerdict.SKIPPED_CLEAR_ENOUGH and not (
            self.settled_facts and self.recommended_next_command
        ):
            raise ValueError(
                "skipped-clear-enough requires settled facts and a concrete next command"
            )
        return self
