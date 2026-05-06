import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.ralph.ralph_prd import read_ralph_prd_artifact
from omx_remote.schemas.ralph.prd_schemas import (
    RalphPrdArtifact,
    TeamAdminAggregationPolicy,
    TeamAdminCompletionPolicy,
    TeamAdminMergePolicy,
    TeamWorkerAuthorizationPolicy,
)


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
        "authorization_policy": "llm_review",
        "authorization_scope": {
            "allowed_commands": ["uv run pytest tests/runtime/test_ralph_control.py -q"],
            "forbidden_commands": ["git push"],
            "requires_human_for": ["modify files outside owned_files"],
            "requires_llm_review_for": ["local checkpoint commit"],
        },
    }

def _team_admin() -> dict[str, object]:
    return {
        "admin_id": "team-admin",
        "aggregation_policy": "collect_all_workers_then_review",
        "merge_policy": "review_before_merge",
        "completion_policy": "all_required_tasks_completed",
        "requires_human_for": ["merge conflicts or worker scope expansion"],
        "requires_llm_review_for": ["final aggregation report before Ralph review"],
        "final_report_required": True,
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


def test_ralph_prd_artifact_requires_team_admin_when_team_fanout_is_enabled() -> None:
    with pytest.raises(ValidationError, match="team_admin is required"):
        RalphPrdArtifact(
            objective="ship Team Admin aggregation contract",
            scope=["make aggregation explicit after Team fanout"],
            constraints=["Ralph owns the admin contract but does not babysit workers"],
            execution_plan=["validate Team Admin policy before Team launch"],
            verification_expectations=["Team DAG sidecar includes admin policy"],
            requires_team_fanout=True,
            team_worker_count=1,
            continuation_policy="review_required",
            team_worker_assignments=[_team_assignment("worker-1", "src/impl.py")],
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
            team_admin=_team_admin(),
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
            team_admin=_team_admin(),
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
            "team_worker_count": 1,
            "continuation_policy": "review_required",
            "team_worker_assignments": [_team_assignment("worker-1", "src/impl.py")],
            "team_admin": _team_admin(),
        },
    )

    result = read_ralph_prd_artifact(prd_path)

    assert result.objective == "ship the first typed prd artifact gate"
    assert result.execution_plan == ("validate .omx/prd.json before launch",)
    assert result.team_worker_count == 1
    assert result.continuation_policy == "review_required"
    assert result.team_admin is not None
    assert result.team_admin.admin_id == "team-admin"


def test_ralph_prd_artifact_promotes_sequence_fields_to_tuple_contracts() -> None:
    artifact = RalphPrdArtifact(
        objective="audit Ralph PRD sequence contracts",
        scope=["replace schema-bound raw lists"],
        constraints=["preserve JSON wire arrays"],
        execution_plan=["write failing tuple contract test"],
        verification_expectations=["tuple fields dump as JSON arrays"],
        requires_team_fanout=False,
        continuation_policy="review_required",
    )

    dumped_artifact = artifact.model_dump(mode="json")

    assert artifact.scope == ("replace schema-bound raw lists",)
    assert artifact.constraints == ("preserve JSON wire arrays",)
    assert artifact.execution_plan == ("write failing tuple contract test",)
    assert artifact.verification_expectations == ("tuple fields dump as JSON arrays",)
    assert dumped_artifact["scope"] == ["replace schema-bound raw lists"]
    assert dumped_artifact["constraints"] == ["preserve JSON wire arrays"]
    assert dumped_artifact["execution_plan"] == ["write failing tuple contract test"]
    assert dumped_artifact["verification_expectations"] == ["tuple fields dump as JSON arrays"]


def test_team_worker_assignment_authorization_policy_emits_stable_wire_value() -> None:
    artifact = RalphPrdArtifact(
        objective="ship worker-level authorization policy",
        scope=["make allow decisions explicit per worker"],
        constraints=["do not let workers widen their own scope"],
        execution_plan=["validate per-worker authorization metadata"],
        verification_expectations=["artifact emits string policy values"],
        requires_team_fanout=True,
        team_worker_count=1,
        continuation_policy="review_required",
        team_worker_assignments=[
            _team_assignment("worker-1", "src/omx_remote/schemas/ralph/prd_schemas.py")
        ],
        team_admin=_team_admin(),
    )

    assignment = artifact.team_worker_assignments[0]
    dumped_artifact = artifact.model_dump(mode="json")

    assert assignment.authorization_policy == TeamWorkerAuthorizationPolicy.LLM_REVIEW
    assert dumped_artifact["team_worker_assignments"][0]["authorization_policy"] == "llm_review"
    assert dumped_artifact["team_worker_assignments"][0]["authorization_scope"] == {
        "allowed_commands": ["uv run pytest tests/runtime/test_ralph_control.py -q"],
        "forbidden_commands": ["git push"],
        "requires_human_for": ["modify files outside owned_files"],
        "requires_llm_review_for": ["local checkpoint commit"],
    }


def test_team_admin_contract_emits_stable_wire_values() -> None:
    artifact = RalphPrdArtifact(
        objective="ship Team Admin aggregation policy",
        scope=["make aggregation explicit"],
        constraints=["Ralph reviews the final Team Admin report"],
        execution_plan=["embed admin policy in Team DAG"],
        verification_expectations=["DAG sidecar includes admin_policy"],
        requires_team_fanout=True,
        team_worker_count=1,
        continuation_policy="review_required",
        team_worker_assignments=[_team_assignment("worker-1", "src/impl.py")],
        team_admin=_team_admin(),
    )

    dumped_artifact = artifact.model_dump(mode="json")

    assert artifact.team_admin is not None
    assert (
        artifact.team_admin.aggregation_policy
        == TeamAdminAggregationPolicy.COLLECT_ALL_WORKERS_THEN_REVIEW
    )
    assert artifact.team_admin.merge_policy == TeamAdminMergePolicy.REVIEW_BEFORE_MERGE
    assert (
        artifact.team_admin.completion_policy
        == TeamAdminCompletionPolicy.ALL_REQUIRED_TASKS_COMPLETED
    )
    assert dumped_artifact["team_admin"] == {
        "admin_id": "team-admin",
        "aggregation_policy": "collect_all_workers_then_review",
        "merge_policy": "review_before_merge",
        "completion_policy": "all_required_tasks_completed",
        "requires_human_for": ["merge conflicts or worker scope expansion"],
        "requires_llm_review_for": ["final aggregation report before Ralph review"],
        "final_report_required": True,
    }


def test_team_worker_assignment_rejects_missing_authorization_policy() -> None:
    assignment_payload = _team_assignment("worker-1", "src/omx_remote/schemas/ralph/prd_schemas.py")
    assignment_payload.pop("authorization_policy")

    with pytest.raises(ValidationError, match="authorization_policy"):
        RalphPrdArtifact(
            objective="ship worker-level authorization policy",
            scope=["make allow decisions explicit per worker"],
            constraints=["do not let workers widen their own scope"],
            execution_plan=["validate per-worker authorization metadata"],
            verification_expectations=["missing policy fails"],
            requires_team_fanout=True,
            team_worker_count=1,
            continuation_policy="review_required",
            team_worker_assignments=[assignment_payload],
        )
