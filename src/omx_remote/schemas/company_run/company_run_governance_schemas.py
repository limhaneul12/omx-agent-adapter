from pydantic import Field, model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.company_run.company_run_core_schemas import (
    CompanyRunArtifactRecord,
)
from omx_remote.shared.omx_enums.agent_enums import AgentEffort
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunBootstrapVoteId,
    CompanyRunEvidenceCheckStatus,
    CompanyRunPhase,
    CompanyRunPhaseStatus,
    CompanyRunVoteChoice,
)


class CompanyRunRouteNextArtifactPayload(StrictSchemaModel):
    """Typed payload for the route-next company-run gate artifact."""

    route: NonEmptyString
    team_required: bool
    subagents_required: bool
    one_agent_show_allowed: bool
    objective: NonEmptyString


class CompanyRunEvidenceCheck(StrictSchemaModel):
    """One explicit evidence check feeding a company-run readiness verdict."""

    check_id: NonEmptyString
    status: CompanyRunEvidenceCheckStatus
    evidence_path: NonEmptyString
    summary: NonEmptyString


class CompanyRunReadinessVerdictPayload(StrictSchemaModel):
    """Typed payload for planning, review, and release readiness verdicts."""

    verdict: NonEmptyString
    required_checks: tuple[CompanyRunEvidenceCheck, ...] = ()
    evidence_paths: tuple[NonEmptyString, ...] = ()
    blocked_reasons: tuple[NonEmptyString, ...] = ()
    note: NonEmptyString | None = None


class CompanyRunTeamPlanPayload(StrictSchemaModel):
    """Typed payload for the implementation Team plan artifact."""

    worker_count: int = Field(ge=3)
    team_required: bool
    scoped_subagents_required: bool
    implementation_before_prd_allowed: bool


class CompanyRunTeamBootstrapArtifacts(StrictSchemaModel):
    """Required artifact existence evidence for the Team bootstrap gate."""

    planning_prd: bool
    planning_test_spec: bool
    planning_execution_brief: bool
    planning_readiness_verdict: bool
    implementation_kickoff: bool


class CompanyRunBootstrapVoteOutcomes(StrictSchemaModel):
    """Typed vote outcomes required before the Team bootstrap gate."""

    research_completion: CompanyRunVoteChoice
    proceed: CompanyRunVoteChoice
    executive_gate: CompanyRunVoteChoice


class CompanyRunBootstrapVoteEvidence(StrictSchemaModel):
    """Vote-file validation evidence for the Team bootstrap gate."""

    outcomes: CompanyRunBootstrapVoteOutcomes
    blocked_reasons: tuple[NonEmptyString, ...]


class CompanyRunRequiredBootstrapVote(StrictSchemaModel):
    """One required vote artifact contract for Team bootstrap validation."""

    gate_id: CompanyRunBootstrapVoteId
    relative_path: NonEmptyString
    vote_id: NonEmptyString
    phase: CompanyRunPhase
    expected_decision: CompanyRunVoteChoice


class CompanyRunWorkerDispatchRecord(StrictSchemaModel):
    """One scoped worker dispatch lane for company-run Team handoff."""

    worker: NonEmptyString
    objective: NonEmptyString
    ownership_boundary: NonEmptyString
    reasoning_effort: AgentEffort
    reasoning_rationale: NonEmptyString
    allowed_subagents: tuple[NonEmptyString, ...]
    subagent_rule: NonEmptyString


class CompanyRunWorkerDispatchPayload(StrictSchemaModel):
    """Typed payload for worker-dispatches.json."""

    workers: tuple[CompanyRunWorkerDispatchRecord, ...]
    blocked_reasons: tuple[NonEmptyString, ...]


class CompanyRunVote(StrictSchemaModel):
    """Small JSON vote artifact used by gate-level files and tests."""

    gate: NonEmptyString
    outcome: CompanyRunVoteChoice
    voter_seat_id: NonEmptyString
    rationale: NonEmptyString
    dissent: bool = False


class CompanyRunVoteBallot(StrictSchemaModel):
    """One council vote with explicit rationale and evidence ownership."""

    voter_id: NonEmptyString
    choice: CompanyRunVoteChoice
    rationale: NonEmptyString
    evidence_path: NonEmptyString


class CompanyRunVoteRecord(StrictSchemaModel):
    """Recorded company-run gate vote."""

    vote_id: NonEmptyString
    phase: CompanyRunPhase
    decision: CompanyRunVoteChoice
    threshold: NonEmptyString
    ballots: tuple[CompanyRunVoteBallot, ...]
    dissent: tuple[NonEmptyString, ...] = ()
    rationale: NonEmptyString

    @model_validator(mode="after")
    def _validate_ballots(self) -> "CompanyRunVoteRecord":
        """Validate ballot authorship within one vote.

        Returns:
            CompanyRunVoteRecord: Validated vote record instance.
        """
        if not self.ballots:
            raise ValueError("company-run votes require at least one ballot")
        voter_ids = [ballot.voter_id for ballot in self.ballots]
        if len(voter_ids) != len(set(voter_ids)):
            raise ValueError("company-run vote voter_id values must be unique")
        return self


class CompanyRunPhaseRecord(StrictSchemaModel):
    """One phase ledger entry for company-run execution."""

    phase: CompanyRunPhase
    status: CompanyRunPhaseStatus
    summary: NonEmptyString
    started_at: NonEmptyString
    finished_at: NonEmptyString | None = None
    artifacts: tuple[CompanyRunArtifactRecord, ...] = ()
    votes: tuple[CompanyRunVoteRecord, ...] = ()
    blocked_reasons: tuple[NonEmptyString, ...] = ()
