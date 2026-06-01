from __future__ import annotations

from pathlib import Path

from omx_remote.runtime.company_run.company_run_result_persistence import (
    actual_company_run_paths,
)
from omx_remote.runtime.company_run.company_run_team_phase import (
    run_team_gate_for_company_run,
)
from omx_remote.runtime.company_run.phase_gates import (
    validate_phase_gate_order,
    validate_team_bootstrap_readiness,
)
from omx_remote.schemas.company_run_schemas import (
    CompanyRunBootstrapVoteOutcomes,
    CompanyRunExecutionRequest,
    CompanyRunPhaseRecord,
    CompanyRunTeamBootstrapArtifacts,
    CompanyRunTeamRequest,
    CompanyRunVoteBallot,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunPhase,
    CompanyRunPhaseStatus,
    CompanyRunVoteChoice,
)

REQUIRED_PHASES = (
    "memory_recall",
    "route_next",
    "research_brief_loop",
    "research_completion_vote",
    "proceed_vote",
    "idea_to_prd",
    "executive_readiness_gate",
    "implementation_kickoff",
    "team_bootstrap",
    "team_sync_loop",
    "integration_plan_loop",
    "review_gate_loop",
    "release_readiness",
    "memory_closeout",
)


def test_company_run_phase_enum_matches_runtime_contract_order() -> None:
    assert tuple(phase.value for phase in CompanyRunPhase) == REQUIRED_PHASES


def test_team_bootstrap_blocks_until_prd_test_spec_and_execution_brief_exist() -> None:
    verdict = validate_team_bootstrap_readiness(
        completed_phases=REQUIRED_PHASES[:7],
        artifacts=CompanyRunTeamBootstrapArtifacts(
            planning_prd=True,
            planning_test_spec=False,
            planning_execution_brief=False,
            planning_readiness_verdict=True,
            implementation_kickoff=False,
        ),
        votes=_valid_bootstrap_votes(),
    )

    assert verdict.allowed is False
    reason_text = "\n".join(str(reason) for reason in verdict.blocked_reasons).lower()
    assert "test-spec" in reason_text
    assert "execution-brief" in reason_text
    assert "implementation-kickoff" in reason_text


def test_team_bootstrap_allows_only_after_ordered_gates_artifacts_and_votes() -> None:
    verdict = validate_team_bootstrap_readiness(
        completed_phases=REQUIRED_PHASES[:8],
        artifacts=_ready_bootstrap_artifacts(),
        votes=_valid_bootstrap_votes(),
    )

    assert verdict.allowed is True
    assert tuple(verdict.blocked_reasons) == ()


def test_phase_gate_order_rejects_skipping_research_and_proceed_votes() -> None:
    verdict = validate_phase_gate_order(
        completed_phases=("memory_recall", "route_next", "idea_to_prd"),
        next_phase="implementation_kickoff",
    )

    assert verdict.allowed is False
    reason_text = "\n".join(str(reason) for reason in verdict.blocked_reasons).lower()
    assert "research_completion_vote" in reason_text
    assert "proceed_vote" in reason_text
    assert "executive_readiness_gate" in reason_text


def test_team_gate_does_not_call_injected_launcher_before_required_gates(
    tmp_path: Path,
) -> None:
    company_root = tmp_path / ".comx-agent" / "runs" / "gate-test" / "company-run"
    company_root.mkdir(parents=True)
    paths = actual_company_run_paths(
        run_id="gate-test",
        run_dir=company_root.parent,
    )
    launched_requests: list[CompanyRunTeamRequest] = []

    request = CompanyRunExecutionRequest.model_validate(
        {
            "objective": "never launch before gates",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "live_team_allowed": False,
        }
    )

    record = run_team_gate_for_company_run(
        paths=paths,
        cwd=tmp_path,
        company_root=company_root,
        request=request,
        live_team_allowed=False,
        phase_records=[],
        team_launcher=launched_requests.append,
    )

    assert launched_requests == []
    assert record.status == "requires_agent_action"
    assert "blocked by company-run readiness gates" in record.note


def test_team_gate_blocks_when_required_vote_file_is_missing(
    tmp_path: Path,
) -> None:
    company_root = _ready_company_root(tmp_path=tmp_path, run_id="missing-vote")
    paths = actual_company_run_paths(
        run_id="missing-vote",
        run_dir=company_root.parent,
    )
    phase_records = _required_phase_records_before_team()
    launched_requests: list[CompanyRunTeamRequest] = []
    request = _execution_request(tmp_path=tmp_path, objective="block missing vote")

    (company_root / "decisions" / "proceed-vote.json").unlink()

    record = run_team_gate_for_company_run(
        paths=paths,
        cwd=tmp_path,
        company_root=company_root,
        request=request,
        live_team_allowed=False,
        phase_records=phase_records,
        team_launcher=launched_requests.append,
    )

    assert launched_requests == []
    assert record.status == "requires_agent_action"
    assert "missing required vote artifact: decisions/proceed-vote.json" in record.note
    assert phase_records[-1].phase == CompanyRunPhase.TEAM_BOOTSTRAP
    assert phase_records[-1].status == CompanyRunPhaseStatus.REQUIRES_AGENT_ACTION
    assert phase_records[-1].blocked_reasons == (record.note,)


def test_team_bootstrap_phase_requires_action_when_live_launch_is_handoff(
    tmp_path: Path,
) -> None:
    company_root = _ready_company_root(tmp_path=tmp_path, run_id="planned-handoff")
    paths = actual_company_run_paths(
        run_id="planned-handoff",
        run_dir=company_root.parent,
    )
    phase_records = _required_phase_records_before_team()
    request = _execution_request(tmp_path=tmp_path, objective="planned Team handoff")

    record = run_team_gate_for_company_run(
        paths=paths,
        cwd=tmp_path,
        company_root=company_root,
        request=request,
        live_team_allowed=False,
        phase_records=phase_records,
        team_launcher=None,
    )

    assert record.status == "requires_agent_action"
    assert phase_records[-1].phase == CompanyRunPhase.TEAM_BOOTSTRAP
    assert phase_records[-1].status == CompanyRunPhaseStatus.REQUIRES_AGENT_ACTION
    assert phase_records[-1].blocked_reasons == (record.note,)


def _ready_bootstrap_artifacts() -> CompanyRunTeamBootstrapArtifacts:
    return CompanyRunTeamBootstrapArtifacts(
        planning_prd=True,
        planning_test_spec=True,
        planning_execution_brief=True,
        planning_readiness_verdict=True,
        implementation_kickoff=True,
    )


def _valid_bootstrap_votes() -> CompanyRunBootstrapVoteOutcomes:
    return CompanyRunBootstrapVoteOutcomes(
        research_completion=CompanyRunVoteChoice.RESEARCH_COMPLETE,
        proceed=CompanyRunVoteChoice.PROCEED_TO_PRD,
        executive_gate=CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
    )


def _ready_company_root(tmp_path: Path, run_id: str) -> Path:
    company_root = tmp_path / ".comx-agent" / "runs" / run_id / "company-run"
    for relative_path in (
        "planning/prd.md",
        "planning/test-spec.md",
        "planning/execution-brief.md",
        "planning/readiness-verdict.json",
        "implementation/implementation-kickoff.md",
    ):
        artifact_path = company_root / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("ready\n", encoding="utf-8")
    _write_vote(
        path=company_root / "research" / "research-vote.json",
        vote_id="research-vote",
        phase=CompanyRunPhase.RESEARCH_COMPLETION_VOTE,
        decision=CompanyRunVoteChoice.RESEARCH_COMPLETE,
    )
    _write_vote(
        path=company_root / "decisions" / "proceed-vote.json",
        vote_id="proceed-vote",
        phase=CompanyRunPhase.PROCEED_VOTE,
        decision=CompanyRunVoteChoice.PROCEED_TO_PRD,
    )
    _write_vote(
        path=company_root / "executive" / "executive-gate.json",
        vote_id="executive-gate",
        phase=CompanyRunPhase.EXECUTIVE_READINESS_GATE,
        decision=CompanyRunVoteChoice.READY_FOR_IMPLEMENTATION,
    )
    return company_root


def _write_vote(
    path: Path,
    vote_id: str,
    phase: CompanyRunPhase,
    decision: CompanyRunVoteChoice,
) -> None:
    vote = CompanyRunVoteRecord(
        vote_id=vote_id,
        phase=phase,
        decision=decision,
        threshold="single test voter",
        ballots=(
            CompanyRunVoteBallot(
                voter_id="test-voter",
                choice=decision,
                rationale="test vote",
                evidence_path=str(path.with_suffix(".md")),
            ),
        ),
        rationale="test rationale",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(vote.model_dump_json(), encoding="utf-8")


def _required_phase_records_before_team() -> list[CompanyRunPhaseRecord]:
    return [
        CompanyRunPhaseRecord(
            phase=CompanyRunPhase(phase_value),
            status=CompanyRunPhaseStatus.COMPLETE,
            summary=f"{phase_value} complete",
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:00Z",
        )
        for phase_value in REQUIRED_PHASES[:8]
    ]


def _execution_request(tmp_path: Path, objective: str) -> CompanyRunExecutionRequest:
    return CompanyRunExecutionRequest.model_validate(
        {
            "objective": objective,
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "live_team_allowed": False,
        }
    )
