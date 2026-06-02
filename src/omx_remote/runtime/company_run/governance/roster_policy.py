from collections.abc import Mapping

from omx_remote.schemas.company_run_schemas import (
    CompanyRunRoster,
    CompanyRunRosterSeat,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import CompanyRunRoleGroup

_MINIMUM_GROUP_SEATS: Mapping[CompanyRunRoleGroup, int] = {
    CompanyRunRoleGroup.CEO: 1,
    CompanyRunRoleGroup.RESEARCH: 3,
    CompanyRunRoleGroup.PRODUCT: 2,
    CompanyRunRoleGroup.EXECUTIVE: 3,
    CompanyRunRoleGroup.TEAM: 3,
    CompanyRunRoleGroup.REVIEW: 3,
}
_MINIMUM_SUBAGENT_CAPABLE_SEATS = 3
_MINIMUM_TOTAL_SEATS = 15


def default_company_run_roster(root_path: str) -> CompanyRunRoster:
    """Build the default non-one-agent company-run roster.

    Args:
        root_path [str]: Company-run artifact root used by ownership paths.

    Returns:
        CompanyRunRoster: Validated default roster.
    """
    seats = (
        CompanyRunRosterSeat(
            seat_id="ceo-orchestrator",
            group=CompanyRunRoleGroup.CEO,
            agent="route_strategist",
            responsibility="Own phase sequencing, votes, escalation, and final accountability.",
            artifact_path=f"{root_path}/decisions/orchestrator-decision.md",
        ),
        CompanyRunRosterSeat(
            seat_id="market-domain-researcher",
            group=CompanyRunRoleGroup.RESEARCH,
            agent="research_analyst",
            responsibility="Research user/domain/ecosystem alternatives and cite evidence.",
            artifact_path=f"{root_path}/research/domain-research.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="technical-feasibility-researcher",
            group=CompanyRunRoleGroup.RESEARCH,
            agent="implementation_architect",
            responsibility="Research architecture feasibility, dependency risks, and integration shape.",
            artifact_path=f"{root_path}/research/technical-feasibility.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="risk-constraint-researcher",
            group=CompanyRunRoleGroup.RESEARCH,
            agent="quality_gatekeeper",
            responsibility="Research security, policy, privacy, operational, and maintenance constraints.",
            artifact_path=f"{root_path}/research/risk-security.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="research-critic",
            group=CompanyRunRoleGroup.RESEARCH,
            agent="research_analyst",
            responsibility="Challenge assumptions, no-build cases, and unknowns before voting.",
            artifact_path=f"{root_path}/research/critic.md",
        ),
        CompanyRunRosterSeat(
            seat_id="pm-prd-writer",
            group=CompanyRunRoleGroup.PRODUCT,
            agent="research_analyst",
            responsibility="Write product goals, users, scope, non-goals, and acceptance criteria.",
            artifact_path=f"{root_path}/prd/prd.md",
        ),
        CompanyRunRosterSeat(
            seat_id="product-architect",
            group=CompanyRunRoleGroup.PRODUCT,
            agent="implementation_architect",
            responsibility="Write architecture constraints and implementation boundaries.",
            artifact_path=f"{root_path}/prd/architecture-notes.md",
        ),
        CompanyRunRosterSeat(
            seat_id="test-spec-writer",
            group=CompanyRunRoleGroup.PRODUCT,
            agent="quality_gatekeeper",
            responsibility="Write test specification and acceptance evidence requirements.",
            artifact_path=f"{root_path}/prd/test-spec.md",
        ),
        CompanyRunRosterSeat(
            seat_id="execution-brief-writer",
            group=CompanyRunRoleGroup.PRODUCT,
            agent="implementation_architect",
            responsibility="Write implementation-ready execution brief and sequencing.",
            artifact_path=f"{root_path}/prd/execution-brief.md",
        ),
        CompanyRunRosterSeat(
            seat_id="cto",
            group=CompanyRunRoleGroup.EXECUTIVE,
            agent="implementation_architect",
            responsibility="Gate technical readiness before implementation kickoff.",
            artifact_path=f"{root_path}/executive/cto-review.md",
        ),
        CompanyRunRosterSeat(
            seat_id="ciso-security",
            group=CompanyRunRoleGroup.EXECUTIVE,
            agent="quality_gatekeeper",
            responsibility="Gate security and permission risks before implementation kickoff.",
            artifact_path=f"{root_path}/executive/ciso-security-review.md",
        ),
        CompanyRunRosterSeat(
            seat_id="qa-lead",
            group=CompanyRunRoleGroup.EXECUTIVE,
            agent="quality_gatekeeper",
            responsibility="Gate testability, QA scenarios, and regression coverage.",
            artifact_path=f"{root_path}/executive/qa-review.md",
        ),
        CompanyRunRosterSeat(
            seat_id="release-manager",
            group=CompanyRunRoleGroup.EXECUTIVE,
            agent="integration_steward",
            responsibility="Gate release, rollback, docs, run-ledger, and memory closeout needs.",
            artifact_path=f"{root_path}/executive/release-readiness-input.md",
        ),
        CompanyRunRosterSeat(
            seat_id="team-worker-frontend-or-surface",
            group=CompanyRunRoleGroup.TEAM,
            agent="executor",
            responsibility="Own one implementation slice and use scoped subagents inside that boundary.",
            artifact_path=f"{root_path}/team/worker-frontend-or-surface.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="team-worker-runtime-or-core",
            group=CompanyRunRoleGroup.TEAM,
            agent="executor",
            responsibility="Own one runtime/core slice and use scoped subagents inside that boundary.",
            artifact_path=f"{root_path}/team/worker-runtime-or-core.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="team-worker-tests-or-qa",
            group=CompanyRunRoleGroup.TEAM,
            agent="test-engineer",
            responsibility="Own tests/QA slice and use scoped verification subagents inside that boundary.",
            artifact_path=f"{root_path}/team/worker-tests-or-qa.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="team-worker-integration",
            group=CompanyRunRoleGroup.TEAM,
            agent="integration_steward",
            responsibility="Own integration, conflict resolution, and merge-order evidence.",
            artifact_path=f"{root_path}/team/worker-integration.md",
            may_spawn_subagents=True,
        ),
        CompanyRunRosterSeat(
            seat_id="code-reviewer",
            group=CompanyRunRoleGroup.REVIEW,
            agent="quality_gatekeeper",
            responsibility="Run correctness and maintainability review gate.",
            artifact_path=f"{root_path}/review/code-review.md",
        ),
        CompanyRunRosterSeat(
            seat_id="security-reviewer",
            group=CompanyRunRoleGroup.REVIEW,
            agent="quality_gatekeeper",
            responsibility="Run security and permission review gate.",
            artifact_path=f"{root_path}/review/security-review.md",
        ),
        CompanyRunRosterSeat(
            seat_id="architecture-reviewer",
            group=CompanyRunRoleGroup.REVIEW,
            agent="implementation_architect",
            responsibility="Run architecture and boundary review gate.",
            artifact_path=f"{root_path}/review/architecture-review.md",
        ),
        CompanyRunRosterSeat(
            seat_id="qa-reviewer",
            group=CompanyRunRoleGroup.REVIEW,
            agent="quality_gatekeeper",
            responsibility="Run QA and test evidence review gate.",
            artifact_path=f"{root_path}/review/qa-verdict.md",
        ),
        CompanyRunRosterSeat(
            seat_id="alexandria-librarian",
            group=CompanyRunRoleGroup.ALEXANDRIA,
            agent="integration_steward",
            responsibility="Plan Alexandria MCP memory recall, librarian lookup, curation, and closeout.",
            artifact_path=f"{root_path}/memory/alexandria-tool-points.md",
        ),
    )
    roster = CompanyRunRoster(seats=seats)
    validate_company_run_roster(roster)
    return roster


def validate_company_run_roster(roster: CompanyRunRoster) -> None:
    """Enforce the company-run no-one-agent and Team/subagent hard gates.

    Args:
        roster [CompanyRunRoster]: Roster to validate.

    Raises:
        ValueError: When the roster cannot satisfy company-run governance.
    """
    if len(roster.seats) < _MINIMUM_TOTAL_SEATS:
        raise ValueError(
            "company-run requires a multi-seat organization; one-agent execution is invalid"
        )

    for group, minimum_count in _MINIMUM_GROUP_SEATS.items():
        group_count = len(roster.seats_for_group(group))
        if group_count < minimum_count:
            raise ValueError(
                f"company-run requires at least {minimum_count} {group} seats; got {group_count}"
            )

    team_seats = roster.seats_for_group(CompanyRunRoleGroup.TEAM)
    subagent_capable = tuple(seat for seat in team_seats if seat.may_spawn_subagents)
    if len(subagent_capable) < _MINIMUM_SUBAGENT_CAPABLE_SEATS:
        raise ValueError(
            "company-run Team workers must include scoped subagent-capable lanes"
        )

    distinct_agents = frozenset(roster.agent_names())
    if len(distinct_agents) < 4:
        raise ValueError(
            "company-run requires at least four distinct configured agent roles"
        )


def validate_vote_authorship(votes: tuple[CompanyRunVoteRecord, ...]) -> None:
    """Reject company-run gates that collapse voting to one lane.

    Args:
        votes [tuple]: Vote records with ballot collections.

    Raises:
        ValueError: When votes are authored by fewer than three lanes.
    """
    voter_ids: set[str] = set()
    for vote in votes:
        for ballot in vote.ballots:
            voter_ids.add(ballot.voter_id)
        if len(vote.ballots) < 3:
            raise ValueError("company-run vote cannot be authored by one or two lanes")
    if len(voter_ids) < 3:
        raise ValueError(
            "company-run votes require at least three distinct voting lanes"
        )
