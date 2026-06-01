from pydantic import Field, model_validator

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunBootstrapVoteId,
    CompanyRunCouncilMode,
    CompanyRunFinalStatus,
    CompanyRunPhase,
    CompanyRunPhaseStatus,
    CompanyRunRoleGroup,
    CompanyRunTeamLaunchMode,
    CompanyRunTeamLaunchStatus,
    CompanyRunVoteChoice,
)

COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS = 1800.0


class CompanyRunRosterSeat(StrictSchemaModel):
    """One company-run seat with bounded ownership and subagent policy."""

    seat_id: NonEmptyString
    group: CompanyRunRoleGroup
    agent: NonEmptyString
    responsibility: NonEmptyString
    artifact_path: NonEmptyString
    may_spawn_subagents: bool = False
    required: bool = True


class CompanyRunRoster(StrictSchemaModel):
    """Validated organization roster for a non-one-agent company-run."""

    seats: tuple[CompanyRunRosterSeat, ...]

    @model_validator(mode="after")
    def _validate_unique_seats(self) -> "CompanyRunRoster":
        """Validate roster seat identity.

        Returns:
            CompanyRunRoster: Validated roster.
        """
        seat_ids = [seat.seat_id for seat in self.seats]
        if len(seat_ids) != len(set(seat_ids)):
            raise ValueError("company-run roster seat_id values must be unique")
        return self

    def seats_for_group(
        self, group: CompanyRunRoleGroup
    ) -> tuple[CompanyRunRosterSeat, ...]:
        """Return seats in one company-run role group.

        Args:
            group [CompanyRunRoleGroup]: Group to select.

        Returns:
            tuple[CompanyRunRosterSeat, ...]: Seats in the group.
        """
        seats: tuple[CompanyRunRosterSeat, ...] = tuple(
            seat for seat in self.seats if seat.group == group
        )
        return seats

    def agent_names(self) -> tuple[str, ...]:
        """Return configured agent names represented in the roster.

        Returns:
            tuple[str, ...]: Agent names for every seat.
        """
        names: tuple[str, ...] = tuple(seat.agent for seat in self.seats)
        return names


class CompanyRunArtifactRecord(StrictSchemaModel):
    """One durable company-run artifact in the run-local index."""

    kind: CompanyRunArtifactKind
    path: NonEmptyString
    required: bool = True
    exists: bool = False
    size_bytes: int = Field(ge=0, default=0)
    sha256: NonEmptyString | None = None
    note: NonEmptyString | None = None


class CompanyRunArtifactIndex(StrictSchemaModel):
    """Public artifact index returned by CLI/MCP status readers."""

    run_id: NonEmptyString
    root_path: NonEmptyString
    artifact_paths: tuple[NonEmptyString, ...]
    artifacts: tuple[CompanyRunArtifactRecord, ...] = ()


class CompanyRunRouteNextArtifactPayload(StrictSchemaModel):
    """Typed payload for the route-next company-run gate artifact."""

    route: NonEmptyString
    team_required: bool
    subagents_required: bool
    one_agent_show_allowed: bool
    objective: NonEmptyString


class CompanyRunReadinessVerdictPayload(StrictSchemaModel):
    """Typed payload for planning/executive review verdict artifacts."""

    verdict: NonEmptyString


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
            CompanyRunVoteRecord: Validated vote record.
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


class CompanyRunTeamLaunchRecord(StrictSchemaModel):
    """OMX Team launch and optional await evidence for company-run."""

    status: CompanyRunTeamLaunchStatus
    command: tuple[NonEmptyString, ...]
    worker_count: int = Field(ge=3)
    team_name: NonEmptyString | None = None
    dispatch_path: NonEmptyString
    launch_stdout_path: NonEmptyString
    launch_stderr_path: NonEmptyString
    await_stdout_path: NonEmptyString | None = None
    await_stderr_path: NonEmptyString | None = None
    exit_code: int | None = None
    await_exit_code: int | None = None
    note: NonEmptyString


class CompanyRunState(StrictSchemaModel):
    """Persisted state snapshot for one actual company-run execution."""

    run_id: NonEmptyString
    objective: NonEmptyString
    cwd: NonEmptyString
    status: CompanyRunFinalStatus
    current_phase: CompanyRunPhase
    roster: CompanyRunRoster
    phases: tuple[CompanyRunPhaseRecord, ...]
    votes: tuple[CompanyRunVoteRecord, ...]
    artifacts: tuple[CompanyRunArtifactRecord, ...]
    team_launch: CompanyRunTeamLaunchRecord | None = None
    alexandria_tool_points: tuple[NonEmptyString, ...]
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CompanyRunExecutionSummary(StrictSchemaModel):
    """Small MCP-friendly company-run execution/status summary."""

    run_id: NonEmptyString
    status: CompanyRunFinalStatus
    state_path: NonEmptyString
    artifact_index_path: NonEmptyString
    company_run_root: NonEmptyString
    team_status: CompanyRunTeamLaunchStatus | None = None
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CompanyRunExecutionRequest(StrictSchemaModel):
    """Public request contract for actual company-run execution."""

    objective: NonEmptyString
    cwd: NonEmptyString
    autonomy: NonEmptyString = "agent"
    notes: NonEmptyString | None = None
    council_mode: CompanyRunCouncilMode = CompanyRunCouncilMode.CODEX
    live_team_allowed: bool = False
    team_launch_mode: CompanyRunTeamLaunchMode = CompanyRunTeamLaunchMode.LAUNCH
    worker_count: int = Field(ge=3, default=4)
    max_research_rounds: int = Field(ge=1, default=2)
    timeout_seconds: float = Field(
        ge=1.0,
        default=COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS,
    )


class CompanyRunTeamRequest(StrictSchemaModel):
    """Injected Team launcher request for company-run engine tests and runtime."""

    native_argv: tuple[NonEmptyString, ...]
    worker_count: int = Field(ge=3)
    objective: NonEmptyString
    team_task: NonEmptyString


class CompanyRunCouncilPromptContext(StrictSchemaModel):
    """Template context for one company-run council prompt asset."""

    role: NonEmptyString
    objective: NonEmptyString
    artifact_label: NonEmptyString
    required_points: NonEmptyString


class CompanyRunTeamPromptContext(StrictSchemaModel):
    """Template context for the company-run Team task prompt asset."""

    objective: NonEmptyString
    company_root: NonEmptyString
    prd_path: NonEmptyString
    test_spec_path: NonEmptyString
    execution_brief_path: NonEmptyString
    kickoff_path: NonEmptyString
    dispatch_path: NonEmptyString


class CompanyRunResult(StrictSchemaModel):
    """MCP-friendly actual company-run execution result."""

    run_id: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    cwd: NonEmptyString
    dry_run: bool
    status: NonEmptyString
    run_dir: NonEmptyString
    result_path: NonEmptyString
    company_run_root: NonEmptyString
    blocked_reasons: tuple[NonEmptyString, ...]
    team_launch_attempted: bool
    team_task: NonEmptyString | None
    artifacts: tuple[NonEmptyString, ...]
    metadata: JsonObject


class CompanyRunArtifactSummaryPayload(StrictSchemaModel):
    """Typed payload for the run-level company-run artifacts summary file."""

    artifact_index_path: NonEmptyString
    artifacts: tuple[NonEmptyString, ...]


class CompanyRunRecordPayload(StrictSchemaModel):
    """Typed payload for the run-level company-run run record file."""

    run_id: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    cwd: NonEmptyString
    dry_run: bool
    status: NonEmptyString
    started_at: NonEmptyString
    finished_at: NonEmptyString
    artifacts: tuple[NonEmptyString, ...]
