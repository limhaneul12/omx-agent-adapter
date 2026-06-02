from omx_remote.schemas.company_run.company_run_core_schemas import CompanyRunRosterSeat
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunVoteBallot,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunPhase,
    CompanyRunVoteChoice,
)


def unanimous_vote_record(
    vote_id: str,
    phase: CompanyRunPhase,
    voters: tuple[CompanyRunRosterSeat, ...],
    decision: CompanyRunVoteChoice,
    rationale: str,
    threshold: str,
) -> CompanyRunVoteRecord:
    """Build a deterministic multi-voter gate record.

    Args:
        vote_id [str]: Stable vote id.
        phase [CompanyRunPhase]: Gate phase.
        voters [tuple[CompanyRunRosterSeat, ...]]: Voting seats.
        decision [CompanyRunVoteChoice]: Gate decision.
        rationale [str]: Shared rationale.
        threshold [str]: Threshold description.

    Returns:
        CompanyRunVoteRecord: Recorded vote.
    """
    if len(voters) < 3:
        raise ValueError("company-run gate votes require at least three voters")
    ballots: tuple[CompanyRunVoteBallot, ...] = tuple(
        CompanyRunVoteBallot(
            voter_id=voter.seat_id,
            choice=decision,
            rationale=f"{voter.responsibility} Evidence supports {decision}.",
            evidence_path=voter.artifact_path,
        )
        for voter in voters
    )
    vote = CompanyRunVoteRecord(
        vote_id=vote_id,
        phase=phase,
        decision=decision,
        threshold=threshold,
        ballots=ballots,
        rationale=rationale,
    )
    return vote
