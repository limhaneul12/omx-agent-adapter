from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.company_run_schemas import (
    CompanyRunBootstrapVoteOutcomes,
    CompanyRunTeamBootstrapArtifacts,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunBootstrapVoteId,
    CompanyRunPhase,
    CompanyRunVoteChoice,
)

_REQUIRED_PHASE_ORDER: tuple[CompanyRunPhase, ...] = tuple(CompanyRunPhase)
_TEAM_BOOTSTRAP_REQUIRED_PHASES: tuple[CompanyRunPhase, ...] = (
    CompanyRunPhase.MEMORY_RECALL,
    CompanyRunPhase.DISCOVERY_GATE,
    CompanyRunPhase.ROUTE_NEXT,
    CompanyRunPhase.RESEARCH_BRIEF_LOOP,
    CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
    CompanyRunPhase.PROCEED_VOTE,
    CompanyRunPhase.IDEA_TO_PRD,
    CompanyRunPhase.EXECUTIVE_READINESS_GATE,
    CompanyRunPhase.IMPLEMENTATION_KICKOFF,
)
_TEAM_BOOTSTRAP_REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "planning/prd.md",
    "planning/test-spec.md",
    "planning/execution-brief.md",
    "planning/readiness-verdict.json",
    "implementation/implementation-kickoff.md",
)
_REQUIRED_BOOTSTRAP_VOTES: tuple[
    tuple[CompanyRunBootstrapVoteId, CompanyRunVoteChoice], ...
] = (
    (
        CompanyRunBootstrapVoteId.RESEARCH_COMPLETION,
        CompanyRunVoteChoice.RESEARCH_COMPLETE,
    ),
    (CompanyRunBootstrapVoteId.PROCEED, CompanyRunVoteChoice.PROCEED_TO_PRD),
    (
        CompanyRunBootstrapVoteId.EXECUTIVE_GATE,
        CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
    ),
)


class CompanyRunGateVerdict(StrictSchemaModel):
    """Boolean gate verdict with explicit blockers."""

    allowed: bool
    blocked_reasons: tuple[NonEmptyString, ...] = ()
    required_artifacts: tuple[NonEmptyString, ...] = ()
    required_phases: tuple[NonEmptyString, ...] = ()


def _phase_value(value: str | CompanyRunPhase) -> str:
    """Normalize a phase token to its string value.

    Args:
        value [str | CompanyRunPhase]: Phase token.

    Returns:
        str: Phase value.
    """
    if isinstance(value, CompanyRunPhase):
        phase_value = value.value
        return phase_value
    return value


def validate_phase_gate_order(
    completed_phases: tuple[str | CompanyRunPhase, ...],
    next_phase: str | CompanyRunPhase,
) -> CompanyRunGateVerdict:
    """Validate that company-run phases cannot skip required earlier gates.

    Args:
        completed_phases [tuple[str | CompanyRunPhase, ...]]: Completed phase values.
        next_phase [str | CompanyRunPhase]: Requested next phase.

    Returns:
        CompanyRunGateVerdict: Gate verdict.
    """
    completed_values = tuple(_phase_value(phase) for phase in completed_phases)
    next_value = _phase_value(next_phase)
    order_values = tuple(phase.value for phase in _REQUIRED_PHASE_ORDER)
    if next_value not in order_values:
        verdict = CompanyRunGateVerdict(
            allowed=False,
            blocked_reasons=(f"unknown company-run phase: {next_value}",),
        )
        return verdict
    next_index = order_values.index(next_value)
    required_before = order_values[:next_index]
    missing = tuple(phase for phase in required_before if phase not in completed_values)
    verdict = CompanyRunGateVerdict(
        allowed=not missing,
        blocked_reasons=tuple(
            f"missing required phase before {next_value}: {phase}" for phase in missing
        ),
        required_phases=required_before,
    )
    return verdict


def validate_team_bootstrap_readiness(
    completed_phases: tuple[str | CompanyRunPhase, ...],
    artifacts: CompanyRunTeamBootstrapArtifacts,
    votes: CompanyRunBootstrapVoteOutcomes,
) -> CompanyRunGateVerdict:
    """Validate PRD/test/execution and votes before OMX Team bootstrap.

    Args:
        completed_phases [tuple[str | CompanyRunPhase, ...]]: Completed phases.
        artifacts [CompanyRunTeamBootstrapArtifacts]: Required artifact evidence.
        votes [CompanyRunBootstrapVoteOutcomes]: Required vote outcomes.

    Returns:
        CompanyRunGateVerdict: Team bootstrap verdict.
    """
    completed_values = tuple(_phase_value(phase) for phase in completed_phases)
    artifact_evidence = (
        ("planning/prd.md", artifacts.planning_prd),
        ("planning/test-spec.md", artifacts.planning_test_spec),
        ("planning/execution-brief.md", artifacts.planning_execution_brief),
        ("planning/readiness-verdict.json", artifacts.planning_readiness_verdict),
        ("implementation/implementation-kickoff.md", artifacts.implementation_kickoff),
    )
    vote_evidence = (
        (CompanyRunBootstrapVoteId.RESEARCH_COMPLETION, votes.research_completion),
        (CompanyRunBootstrapVoteId.PROCEED, votes.proceed),
        (CompanyRunBootstrapVoteId.EXECUTIVE_GATE, votes.executive_gate),
    )
    phase_blockers = [
        f"missing required phase before team_bootstrap: {phase.value}"
        for phase in _TEAM_BOOTSTRAP_REQUIRED_PHASES
        if phase.value not in completed_values
    ]
    artifact_blockers = [
        f"missing required Team bootstrap artifact: {artifact}"
        for artifact, exists in artifact_evidence
        if not exists
    ]
    vote_blockers = [
        f"missing required vote {vote_id.value}: expected {expected_outcome.value}"
        for (vote_id, expected_outcome), (_, actual_outcome) in zip(
            _REQUIRED_BOOTSTRAP_VOTES,
            vote_evidence,
            strict=True,
        )
        if actual_outcome != expected_outcome
    ]
    blocked: list[str] = [*phase_blockers, *artifact_blockers, *vote_blockers]
    verdict = CompanyRunGateVerdict(
        allowed=not blocked,
        blocked_reasons=tuple(blocked),
        required_artifacts=_TEAM_BOOTSTRAP_REQUIRED_ARTIFACTS,
        required_phases=tuple(phase.value for phase in _TEAM_BOOTSTRAP_REQUIRED_PHASES),
    )
    return verdict
