from __future__ import annotations

from pathlib import Path

import pytest

from omx_remote.runtime.company_run.artifact_index import (
    REQUIRED_COMPANY_RUN_ARTIFACTS,
    build_company_run_artifact_index,
)
from omx_remote.runtime.company_run.company_run_worker_dispatch import (
    WORKER_BOUNDARY_SUBAGENT_RULE,
    build_worker_dispatch_payload,
)
from omx_remote.schemas.company_run_schemas import (
    CompanyRunArtifactIndex,
    CompanyRunVote,
)
from omx_remote.shared.utils.json_model_dump import model_json_object

REQUIRED_ARTIFACTS = {
    "state.json",
    "roster.json",
    "phase-log.jsonl",
    "memory-recall.md",
    "discovery/discovery-decision-packet.json",
    "discovery/discovery-summary.md",
    "discovery/roi-no-build-gate.json",
    "discovery/deep-interview-handoff.md",
    "decisions/discovery-decision-report.json",
    "decisions/discovery-decision-report.md",
    "route-next.json",
    "research/domain-research.md",
    "research/technical-feasibility.md",
    "research/risk-security.md",
    "research/critic.md",
    "research/research-vote.json",
    "decisions/proceed-vote.json",
    "decisions/orchestrator-decision.md",
    "planning/prd.md",
    "planning/test-spec.md",
    "planning/execution-brief.md",
    "planning/risks-and-decisions.md",
    "planning/readiness-verdict.json",
    "executive/cto-review.md",
    "executive/ciso-security-review.md",
    "executive/qa-review.md",
    "executive/release-manager-review.md",
    "executive/executive-gate.json",
    "implementation/implementation-kickoff.md",
    "implementation/team-plan.json",
    "implementation/team-launch.json",
    "team/team-sync.md",
    "team/worker-dispatches.json",
    "team/integration-plan.md",
    "review/review-gate.json",
    "review/code-review.md",
    "review/security-review.md",
    "review/architecture-review.md",
    "review/qa-verdict.md",
    "release/release-readiness.json",
    "release/release-summary.md",
    "memory-closeout.md",
}


def test_required_artifact_contract_is_complete_and_relative_to_company_run_root() -> (
    None
):
    actual = {str(path) for path in REQUIRED_COMPANY_RUN_ARTIFACTS}

    assert actual == REQUIRED_ARTIFACTS
    assert all(not Path(path).is_absolute() for path in actual)
    assert all(".." not in Path(path).parts for path in actual)


def test_artifact_index_points_inside_actual_run_company_run_directory(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / ".comx-agent" / "runs" / "20260601T010203Z-company-run"

    artifact_index = build_company_run_artifact_index(run_dir=run_dir)
    validated = CompanyRunArtifactIndex.model_validate(
        model_json_object(artifact_index)
    )

    root = run_dir / "company-run"
    paths = tuple(str(path) for path in validated.artifact_paths)
    assert str(root / "state.json") in paths
    assert str(root / "discovery" / "discovery-decision-packet.json") in paths
    assert str(root / "decisions" / "discovery-decision-report.md") in paths
    assert str(root / "planning" / "prd.md") in paths
    assert str(root / "planning" / "test-spec.md") in paths
    assert str(root / "planning" / "execution-brief.md") in paths
    assert str(root / "research" / "research-vote.json") in paths
    assert str(root / "decisions" / "proceed-vote.json") in paths
    assert str(root / "implementation" / "team-launch.json") in paths
    assert all(Path(path).is_relative_to(root) for path in paths)


def test_vote_artifacts_are_json_contracts_with_gate_outcomes() -> None:
    research_vote = CompanyRunVote.model_validate(
        {
            "gate": "research_completion",
            "outcome": "research-complete",
            "voter_seat_id": "research-1",
            "rationale": "Enough domain, technical, and risk evidence exists.",
            "dissent": False,
        }
    )
    proceed_vote = CompanyRunVote.model_validate(
        {
            "gate": "proceed",
            "outcome": "proceed-to-prd",
            "voter_seat_id": "ceo",
            "rationale": "Proceed to PRD with recorded risks.",
            "dissent": False,
        }
    )

    assert research_vote.outcome == "research-complete"
    assert proceed_vote.outcome == "proceed-to-prd"


def test_worker_dispatches_use_separate_ownership_lanes() -> None:
    dispatch_payload = build_worker_dispatch_payload(
        objective="ship scoped company-run work",
        worker_count=8,
        allowed_subagents=("executor", "test-engineer"),
        subagent_rule=WORKER_BOUNDARY_SUBAGENT_RULE,
    )

    boundaries = tuple(worker.ownership_boundary for worker in dispatch_payload.workers)
    assert len(boundaries) == 8
    assert len(set(boundaries)) == len(boundaries)
    assert boundaries[0] != boundaries[1]
    assert boundaries[0].startswith("worker-1 ownership lane:")
    assert boundaries[1].startswith("worker-2 ownership lane:")
    assert "extension slice 2" in boundaries[-1]


def test_worker_dispatches_scope_codex_subagents_to_worker_boundary() -> None:
    dispatch_payload = build_worker_dispatch_payload(
        objective="ship scoped company-run work",
        worker_count=3,
        allowed_subagents=("executor", "test-engineer", "code-reviewer"),
        subagent_rule=WORKER_BOUNDARY_SUBAGENT_RULE,
    )

    for worker in dispatch_payload.workers:
        assert worker.subagent_rule == WORKER_BOUNDARY_SUBAGENT_RULE
        assert worker.allowed_subagents == (
            "executor",
            "test-engineer",
            "code-reviewer",
        )


def test_worker_dispatches_reject_unscoped_subagent_rule() -> None:
    with pytest.raises(ValueError, match="scoped Codex subagent boundary rule"):
        build_worker_dispatch_payload(
            objective="ship scoped company-run work",
            worker_count=2,
            allowed_subagents=("executor",),
            subagent_rule="subagents may inspect any lane",
        )


def test_worker_dispatches_reject_missing_scoped_subagents() -> None:
    with pytest.raises(ValueError, match="at least one scoped Codex subagent"):
        build_worker_dispatch_payload(
            objective="ship scoped company-run work",
            worker_count=2,
            allowed_subagents=(),
            subagent_rule=WORKER_BOUNDARY_SUBAGENT_RULE,
        )
