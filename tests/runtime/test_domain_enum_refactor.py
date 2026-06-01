from enum import StrEnum
from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.ralph.ralph_state import RalphStateClassifier
from omx_remote.runtime.ultrawork.ultrawork_control import UltraworkStateClassifier
from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalExecutionShape,
    CodexGoalHandoffState,
    CodexGoalLaunchRequest,
    CodexGoalMirrorState,
    CodexGoalReviewPolicy,
    CodexGoalTrackingState,
)
from omx_remote.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from omx_remote.schemas.multi_operator_snapshot_schemas import (
    FlowSelector,
    ManagedFlowKind,
)
from omx_remote.schemas.operator_action_schemas import (
    OperatorActionResult,
    OperatorLoopState,
)
from omx_remote.schemas.runtime_status_schemas import (
    RuntimeModeSnapshot,
    RuntimeModeStatus,
    RuntimeStatusAnomaly,
    RuntimeStatusAnomalyCategory,
)
from omx_remote.shared.omx_enums.codex_goal_enums import CodexGoalMirrorSource
from omx_remote.shared.omx_enums.ralph_enums import RalphStateClassification
from omx_remote.shared.omx_enums.ultrawork_enums import UltraworkStateClassification
from omx_remote.shared.utils.json_model_dump import model_json_object


def test_schema_contracts_are_moved_without_flat_wrapper_modules() -> None:
    schema_root = Path(__file__).parents[2] / "src" / "omx_remote" / "schemas"
    removed_wrapper_names = {
        "codex_goal_schemas.py",
        "codex_goal_runtime_schemas.py",
        "multi_operator_schemas.py",
        "operator_schemas.py",
        "ralph_prd_schemas.py",
        "runtime_schemas.py",
    }

    remaining_wrapper_paths = [
        wrapper_path
        for wrapper_path in schema_root.iterdir()
        if wrapper_path.name in removed_wrapper_names
    ]

    assert remaining_wrapper_paths == []


def test_strict_schema_base_uses_agreed_contract_config() -> None:
    assert StrictSchemaModel.model_config["extra"] == "forbid"
    assert StrictSchemaModel.model_config["frozen"] is True
    assert StrictSchemaModel.model_config["use_enum_values"] is True
    assert StrictSchemaModel.model_config["validate_default"] is True


def test_strict_root_schema_base_uses_root_contract_config() -> None:
    assert StrictRootSchemaModel.model_config.get("extra") is None
    assert StrictRootSchemaModel.model_config["frozen"] is True
    assert StrictRootSchemaModel.model_config["use_enum_values"] is True
    assert StrictRootSchemaModel.model_config["validate_default"] is True


def test_enum_classes_have_concept_docstrings() -> None:
    enum_classes = [
        CodexGoalExecutionShape,
        CodexGoalHandoffState,
        CodexGoalMirrorSource,
        CodexGoalReviewPolicy,
        CodexGoalTrackingState,
        ManagedFlowKind,
        OperatorLoopState,
        RuntimeModeStatus,
        RuntimeStatusAnomalyCategory,
        RalphStateClassification,
        UltraworkStateClassification,
    ]

    for enum_class in enum_classes:
        assert issubclass(enum_class, StrEnum)
        assert enum_class.__doc__ is not None
        assert enum_class.__doc__.strip() != ""


def test_strict_schema_config_normalizes_enum_members_to_json_strings() -> None:
    request = CodexGoalLaunchRequest(
        objective_text="check config dict enum behavior",
        execution_shape="ralph_pipeline",
        review_policy="continue_automatically",
        team_worker_count=2,
    )

    assert request.execution_shape == "ralph_pipeline"
    assert request.model_dump()["execution_shape"] == "ralph_pipeline"
    assert model_json_object(request)["execution_shape"] == "ralph_pipeline"
    request = CodexGoalLaunchRequest.model_validate(
        {
            "objective_text": "ship typed enum contracts",
            "execution_shape": "ralph_pipeline",
            "review_policy": "review_required",
            "team_worker_count": 2,
        }
    )

    assert request.execution_shape == CodexGoalExecutionShape.RALPH_PIPELINE.value
    assert request.review_policy == CodexGoalReviewPolicy.REVIEW_REQUIRED.value
    assert model_json_object(request)["execution_shape"] == "ralph_pipeline"


@pytest.mark.parametrize(
    ("field_name", "enum_member"),
    [
        ("source", CodexGoalMirrorSource.CODEX_GOAL),
        ("handoff_state", CodexGoalHandoffState.AWAITING_RALPH),
        ("tracking_state", CodexGoalTrackingState.ACTIVE),
    ],
)
def test_codex_goal_mirror_state_accepts_enum_or_string_values(
    field_name: str,
    enum_member: object,
) -> None:
    payload: dict[str, object] = {
        "goal_id": "goal-1",
        "objective_text": "objective",
        "source": "codex_goal",
        "execution_shape": CodexGoalExecutionShape.RALPH_PIPELINE,
        "review_policy": "continue_automatically",
        "team_worker_count": 1,
        "working_directory": "/tmp/repo",
        "codex_command": ["codex", "--enable", "goals"],
        "session_locator": "codex-goal-goal-1",
        "launched_at": "2026-01-01T00:00:00Z",
        "handoff_state": "awaiting_ralph",
        "tracking_state": "active",
    }
    payload[field_name] = enum_member

    result = CodexGoalMirrorState.model_validate(payload)

    assert model_json_object(result)[field_name] == str(enum_member)


def test_runtime_and_operator_schemas_use_enum_backed_fields() -> None:
    runtime_snapshot = RuntimeModeSnapshot(
        name="ralph",
        status="active",
        raw_status_text="ACTIVE (phase: starting)",
        has_uncertainty=False,
    )
    anomaly = RuntimeStatusAnomaly(
        category="unknown_mode_status",
        message="odd state",
    )
    operator_result = OperatorActionResult(
        lane="ralph",
        action="resume",
        loop_state="resumable_later",
        next_action="resume",
        summary="Ralph can resume",
    )

    assert runtime_snapshot.status == RuntimeModeStatus.ACTIVE.value
    assert anomaly.category == RuntimeStatusAnomalyCategory.UNKNOWN_MODE_STATUS.value
    assert operator_result.loop_state == OperatorLoopState.RESUMABLE_LATER.value
    assert model_json_object(operator_result)["loop_state"] == "resumable_later"


@pytest.mark.parametrize("invalid_status", ["started", "blocked", "finished"])
def test_runtime_status_enum_rejects_unknown_statuses(invalid_status: str) -> None:
    with pytest.raises(ValidationError):
        RuntimeModeSnapshot(
            name="ralph",
            status=invalid_status,
            raw_status_text=invalid_status,
            has_uncertainty=True,
        )


def test_multi_operator_schema_uses_managed_flow_kind_enum() -> None:
    selector = FlowSelector(repo_id="repo-a", flow_id="repo-a:ralph")
    _ = selector
    flow_kind = ManagedFlowKind.RALPH

    assert flow_kind == "ralph"
    assert str(flow_kind) == "ralph"


def test_ralph_state_classifier_groups_phase_and_outcome_sets() -> None:
    resumable_state = RalphStateClassifier.classify_state_snapshot(
        {"active": False, "current_phase": "planning"}
    )
    terminal_state = RalphStateClassifier.classify_state_snapshot(
        {"active": False, "run_outcome": "done"}
    )
    stale_state = RalphStateClassifier.classify_state_snapshot({"active": "yes"})

    assert resumable_state is RalphStateClassification.RESUMABLE
    assert terminal_state is RalphStateClassification.TERMINAL
    assert stale_state is RalphStateClassification.STALE


def test_ultrawork_state_classifier_groups_phase_and_outcome_sets() -> None:
    resumable_state = UltraworkStateClassifier.classify_state_snapshot(
        {"active": False, "current_phase": "planning"}
    )
    terminal_state = UltraworkStateClassifier.classify_state_snapshot(
        {"active": False, "run_outcome": "done"}
    )
    stale_state = UltraworkStateClassifier.classify_state_snapshot({"active": "yes"})

    assert resumable_state is UltraworkStateClassification.RESUMABLE
    assert terminal_state is UltraworkStateClassification.TERMINAL
    assert stale_state is UltraworkStateClassification.STALE
