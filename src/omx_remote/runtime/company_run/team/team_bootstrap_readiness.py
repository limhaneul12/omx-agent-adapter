from pathlib import Path

from pydantic import ValidationError

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunBootstrapVoteEvidence,
    CompanyRunBootstrapVoteOutcomes,
    CompanyRunRequiredBootstrapVote,
    CompanyRunTeamBootstrapArtifacts,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunBootstrapVoteId,
    CompanyRunPhase,
    CompanyRunVoteChoice,
)

_RESEARCH_COMPLETION_VOTE = CompanyRunRequiredBootstrapVote(
    gate_id=CompanyRunBootstrapVoteId.RESEARCH_COMPLETION,
    relative_path="research/research-vote.json",
    vote_id="research-vote",
    phase=CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
    expected_decision=CompanyRunVoteChoice.RESEARCH_COMPLETE,
)
_PROCEED_VOTE = CompanyRunRequiredBootstrapVote(
    gate_id=CompanyRunBootstrapVoteId.PROCEED,
    relative_path="decisions/proceed-vote.json",
    vote_id="proceed-vote",
    phase=CompanyRunPhase.PROCEED_VOTE,
    expected_decision=CompanyRunVoteChoice.PROCEED_TO_PRD,
)
_EXECUTIVE_GATE_VOTE = CompanyRunRequiredBootstrapVote(
    gate_id=CompanyRunBootstrapVoteId.EXECUTIVE_GATE,
    relative_path="executive/executive-gate.json",
    vote_id="executive-gate",
    phase=CompanyRunPhase.EXECUTIVE_READINESS_GATE,
    expected_decision=CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
)

def _team_bootstrap_artifact_evidence(
    company_root: Path,
) -> CompanyRunTeamBootstrapArtifacts:
    """Collect required artifact existence evidence for Team bootstrap.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.

    Returns:
        CompanyRunTeamBootstrapArtifacts: Typed artifact gate evidence.
    """
    evidence = CompanyRunTeamBootstrapArtifacts(
        planning_prd=(company_root / "planning" / "prd.md").is_file(),
        planning_test_spec=(company_root / "planning" / "test-spec.md").is_file(),
        planning_execution_brief=(
            company_root / "planning" / "execution-brief.md"
        ).is_file(),
        planning_readiness_verdict=(
            company_root / "planning" / "readiness-verdict.json"
        ).is_file(),
        implementation_kickoff=(
            company_root / "implementation" / "implementation-kickoff.md"
        ).is_file(),
    )
    return evidence


def _team_bootstrap_vote_evidence(
    company_root: Path,
) -> CompanyRunBootstrapVoteEvidence:
    """Read and validate the vote files required before Team bootstrap.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.

    Returns:
        CompanyRunBootstrapVoteEvidence: Vote outcomes plus file/schema blockers.
    """
    research_vote = _read_required_bootstrap_vote(
        company_root=company_root,
        vote_spec=_RESEARCH_COMPLETION_VOTE,
    )
    proceed_vote = _read_required_bootstrap_vote(
        company_root=company_root,
        vote_spec=_PROCEED_VOTE,
    )
    executive_vote = _read_required_bootstrap_vote(
        company_root=company_root,
        vote_spec=_EXECUTIVE_GATE_VOTE,
    )
    evidence = CompanyRunBootstrapVoteEvidence(
        outcomes=CompanyRunBootstrapVoteOutcomes(
            research_completion=research_vote.decision,
            proceed=proceed_vote.decision,
            executive_gate=executive_vote.decision,
        ),
        blocked_reasons=(
            *research_vote.blocked_reasons,
            *proceed_vote.blocked_reasons,
            *executive_vote.blocked_reasons,
        ),
    )
    return evidence


class _RequiredVoteReadResult(StrictSchemaModel):
    """Internal result for one required bootstrap vote artifact."""

    decision: CompanyRunVoteChoice
    blocked_reasons: tuple[NonEmptyString, ...]


def _read_required_bootstrap_vote(
    company_root: Path,
    vote_spec: CompanyRunRequiredBootstrapVote,
) -> _RequiredVoteReadResult:
    """Read one required Team-bootstrap vote file as a typed vote record.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        vote_spec [CompanyRunRequiredBootstrapVote]: Expected vote contract.

    Returns:
        _RequiredVoteReadResult: Decision and blockers for one vote file.
    """
    vote_path = company_root / vote_spec.relative_path
    if not vote_path.is_file():
        result = _RequiredVoteReadResult(
            decision=CompanyRunVoteChoice.BLOCK,
            blocked_reasons=(
                f"missing required vote artifact: {vote_spec.relative_path}",
            ),
        )
        return result
    try:
        vote_record = CompanyRunVoteRecord.model_validate_json(vote_path.read_bytes())
    except (OSError, ValidationError, ValueError) as error:
        result = _RequiredVoteReadResult(
            decision=CompanyRunVoteChoice.BLOCK,
            blocked_reasons=(
                f"invalid required vote artifact {vote_spec.relative_path}: {error}",
            ),
        )
        return result

    identity_blockers = _required_vote_identity_blockers(
        vote_spec=vote_spec,
        vote_record=vote_record,
    )
    decision = (
        vote_record.decision if not identity_blockers else CompanyRunVoteChoice.BLOCK
    )
    result = _RequiredVoteReadResult(
        decision=decision,
        blocked_reasons=identity_blockers,
    )
    return result


def _required_vote_identity_blockers(
    vote_spec: CompanyRunRequiredBootstrapVote,
    vote_record: CompanyRunVoteRecord,
) -> tuple[str, ...]:
    """Return identity blockers for a vote file that parsed successfully.

    Args:
        vote_spec [CompanyRunRequiredBootstrapVote]: Expected vote contract.
        vote_record [CompanyRunVoteRecord]: Parsed vote record.

    Returns:
        tuple[str, ...]: Identity mismatch blockers.
    """
    blockers = [
        (
            f"invalid vote_id in {vote_spec.relative_path}: expected "
            f"{vote_spec.vote_id}, got {vote_record.vote_id}"
        )
        for expected, actual in ((vote_spec.vote_id, vote_record.vote_id),)
        if actual != expected
    ]
    blockers.extend(
        (
            f"invalid vote phase in {vote_spec.relative_path}: expected "
            f"{vote_spec.phase.value}, got {vote_record.phase.value}"
        )
        for expected, actual in ((vote_spec.phase, vote_record.phase),)
        if actual != expected
    )
    return tuple(blockers)

