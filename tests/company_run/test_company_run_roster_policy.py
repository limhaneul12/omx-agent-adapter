from __future__ import annotations

import pytest

from omx_remote.runtime.company_run.governance.roster_policy import (
    validate_company_run_roster,
    validate_vote_authorship,
)
from omx_remote.schemas.company_run.company_run_core_schemas import CompanyRunRoster
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunVoteBallot,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import CompanyRunRoleGroup
from omx_remote.shared.utils.json_model_dump import model_json_object


def _seat(
    group: str,
    seat_id: str,
    agent: str | None = None,
    may_spawn_subagents: bool = False,
) -> dict[str, object]:
    return {
        "group": group,
        "seat_id": seat_id,
        "agent": agent or seat_id,
        "responsibility": f"{seat_id} responsibility",
        "artifact_path": f"company-run/{seat_id}.md",
        "may_spawn_subagents": may_spawn_subagents,
    }


def _minimum_roster_payload() -> dict[str, object]:
    seats: list[dict[str, object]] = [_seat("ceo", "ceo", "route_strategist")]
    seats.extend(
        _seat("research", f"research-{index}", f"research_{index}")
        for index in range(1, 4)
    )
    seats.extend(
        _seat("product", f"product-{index}", f"product_{index}")
        for index in range(1, 3)
    )
    seats.extend(
        _seat("executive", f"executive-{index}", f"executive_{index}")
        for index in range(1, 4)
    )
    seats.extend(
        _seat(
            "team",
            f"worker-{index}",
            f"worker_{index}",
            may_spawn_subagents=True,
        )
        for index in range(1, 4)
    )
    seats.extend(
        _seat("review", f"review-{index}", f"review_{index}") for index in range(1, 4)
    )
    return {"seats": seats}


def _roster(payload: dict[str, object]) -> CompanyRunRoster:
    return CompanyRunRoster.model_validate(payload)


def _validate_roster(roster: CompanyRunRoster) -> None:
    validate_company_run_roster(roster=roster)


def test_one_agent_roster_blocks_before_any_company_run_mutation() -> None:
    roster = _roster(
        {
            "seats": [
                _seat("ceo", "only-seat", "single_agent"),
                _seat("research", "research-1", "single_agent"),
                _seat("product", "product-1", "single_agent"),
                _seat("executive", "executive-1", "single_agent"),
                _seat("team", "worker-1", "single_agent", may_spawn_subagents=True),
            ]
        }
    )

    with pytest.raises(ValueError, match="one-agent|multi-seat|distinct"):
        _validate_roster(roster)


def test_missing_minimum_councils_team_or_subagents_blocks_execution() -> None:
    roster = _roster(
        {
            "seats": [
                _seat("ceo", "ceo", "route_strategist"),
                _seat("research", "research-1", "research_analyst"),
                _seat("product", "product-1", "product_writer"),
                _seat("executive", "executive-1", "cto"),
            ]
        }
    )

    with pytest.raises(ValueError, match="requires"):
        _validate_roster(roster)


def test_minimum_company_roster_passes_and_preserves_distinct_lanes() -> None:
    roster = _roster(_minimum_roster_payload())

    _validate_roster(roster)

    groups = [seat.group for seat in roster.seats]
    assert groups.count(CompanyRunRoleGroup.CEO) == 1
    assert groups.count(CompanyRunRoleGroup.RESEARCH) >= 3
    assert groups.count(CompanyRunRoleGroup.PRODUCT) >= 2
    assert groups.count(CompanyRunRoleGroup.EXECUTIVE) >= 3
    assert groups.count(CompanyRunRoleGroup.TEAM) >= 3
    assert sum(1 for seat in roster.seats if seat.may_spawn_subagents) >= 3
    assert len(set(roster.agent_names())) > 1


def test_vote_authorship_by_one_lane_is_rejected() -> None:
    ballot = CompanyRunVoteBallot.model_validate(
        {
            "voter_id": "ceo",
            "choice": "research-complete",
            "rationale": "single lane vote",
            "evidence_path": "company-run/decisions/orchestrator-decision.md",
        }
    )
    votes = tuple(
        CompanyRunVoteRecord.model_validate(
            {
                "vote_id": vote_id,
                "phase": phase,
                "decision": decision,
                "threshold": "minimum council",
                "ballots": [model_json_object(ballot)],
                "rationale": f"{vote_id} rationale",
            }
        )
        for vote_id, phase, decision in (
            ("research-vote", "research_completion_vote", "research-complete"),
            ("proceed-vote", "proceed_vote", "proceed-to-prd"),
            ("release-vote", "release_readiness", "approve"),
        )
    )

    with pytest.raises(ValueError, match="vote|one|single|lane"):
        validate_vote_authorship(votes=votes)
