import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.ralph_control import read_ralph_prd_artifact
from omx_remote.schemas.ralph import RalphPrdArtifact


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _team_assignment(worker_id: str, owned_file: str) -> dict[str, object]:
    return {
        "worker_id": worker_id,
        "lane_name": f"{worker_id} lane",
        "objective": "own one safe lane",
        "owned_files": [owned_file],
        "read_only_context_files": ["docs/jobs/schema-type-refactor-hardening/8_ralph-prd-to-team-worker-distribution-prompt.md"],
        "forbidden_files": ["src/omx_remote/runtime/codex_goal_supervisor.py"],
        "tdd_steps": ["write failing regression", "make it pass"],
        "verification_commands": ["uv run pytest tests/runtime/test_ralph_control.py -q"],
        "handoff_summary_required": "report changed files and verification output",
    }



def test_ralph_prd_artifact_rejects_missing_execution_plan() -> None:
    with pytest.raises(ValidationError):
        RalphPrdArtifact(
            objective="ship the first typed prd artifact gate",
            scope=["tighten the local ralph preflight contract"],
            constraints=["keep ralph independently operable"],
            verification_expectations=["ralph launch rejects malformed prd.json"],
            requires_team_fanout=False,
            continuation_policy="review_required",
        )



def test_ralph_prd_artifact_requires_team_worker_count_when_team_fanout_is_enabled() -> None:
    with pytest.raises(ValidationError):
        RalphPrdArtifact(
            objective="ship the first typed prd artifact gate",
            scope=["tighten the local ralph preflight contract"],
            constraints=["keep ralph independently operable"],
            execution_plan=["validate .omx/prd.json before launch"],
            verification_expectations=["ralph launch rejects malformed prd.json"],
            requires_team_fanout=True,
            continuation_policy="review_required",
        )


def test_ralph_prd_artifact_rejects_assignment_count_that_mismatches_worker_count() -> None:
    with pytest.raises(ValidationError, match="team_worker_assignments length"):
        RalphPrdArtifact(
            objective="ship the first typed prd artifact gate",
            scope=["tighten the local ralph preflight contract"],
            constraints=["keep ralph independently operable"],
            execution_plan=["validate .omx/prd.json before launch"],
            verification_expectations=["ralph launch rejects malformed prd.json"],
            requires_team_fanout=True,
            team_worker_count=2,
            continuation_policy="review_required",
            team_worker_assignments=[_team_assignment("worker-1", "src/impl.py")],
        )


def test_ralph_prd_artifact_rejects_duplicate_owned_files_across_assignments() -> None:
    with pytest.raises(ValidationError, match="duplicate owned_files"):
        RalphPrdArtifact(
            objective="ship the first typed prd artifact gate",
            scope=["tighten the local ralph preflight contract"],
            constraints=["keep ralph independently operable"],
            execution_plan=["validate .omx/prd.json before launch"],
            verification_expectations=["ralph launch rejects malformed prd.json"],
            requires_team_fanout=True,
            team_worker_count=2,
            continuation_policy="review_required",
            team_worker_assignments=[
                _team_assignment("worker-1", "src/shared.py"),
                _team_assignment("worker-2", "src/shared.py"),
            ],
        )



def test_read_ralph_prd_artifact_returns_typed_contract_for_valid_file(tmp_path: Path) -> None:
    prd_path = tmp_path / ".omx" / "prd.json"
    prd_path.parent.mkdir(parents=True)
    _write_json(
        prd_path,
        {
            "objective": "ship the first typed prd artifact gate",
            "scope": ["tighten the local ralph preflight contract"],
            "constraints": ["keep ralph independently operable"],
            "execution_plan": ["validate .omx/prd.json before launch"],
            "verification_expectations": ["ralph launch rejects malformed prd.json"],
            "requires_team_fanout": True,
            "team_worker_count": 4,
            "continuation_policy": "review_required",
        },
    )

    result = read_ralph_prd_artifact(prd_path)

    assert result.objective == "ship the first typed prd artifact gate"
    assert result.execution_plan == ["validate .omx/prd.json before launch"]
    assert result.team_worker_count == 4
    assert result.continuation_policy == "review_required"
