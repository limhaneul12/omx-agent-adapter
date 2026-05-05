import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.ralph_control import read_ralph_prd_artifact
from omx_remote.schemas.ralph import RalphPrdArtifact



def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")



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
