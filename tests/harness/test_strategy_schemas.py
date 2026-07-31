from pathlib import Path

import pytest
from comx_harness.schemas.strategy_schemas import (
    StrategyDefinition,
    StrategyStage,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    NativeCapability,
    StrategyNodeType,
    StrategyValidatorKind,
)
from pydantic import ValidationError


def _workspace(tmp_path: Path) -> str:
    return str(tmp_path.resolve())


def test_strategy_schema_accepts_a_bounded_cross_provider_sequence(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)

    strategy = StrategyDefinition(
        strategy_id="review-sequence",
        mission="Implement with Codex and verify with OMX.",
        stages=(
            StrategyStage(
                stage_id="codex-implement",
                node_type=StrategyNodeType.NATIVE_RUN,
                provider=ProviderId.CODEX,
                native_surface="exec",
                objective="Inspect the workspace without mutation.",
                workspace=workspace,
                expected_artifacts=("review.md",),
                capability_requirements=(
                    NativeCapability.DETACHED_EXECUTION,
                    NativeCapability.STRUCTURED_EVENTS,
                ),
            ),
            StrategyStage(
                stage_id="omx-review",
                node_type=StrategyNodeType.HANDOFF,
                provider=ProviderId.OMX,
                objective="Review the verified Codex result.",
                workspace=workspace,
                dependencies=("codex-implement",),
                source_stage_id="codex-implement",
                input_artifacts=("result",),
                capability_requirements=(NativeCapability.ARTIFACTS,),
            ),
            StrategyStage(
                stage_id="validate",
                node_type=StrategyNodeType.VALIDATOR,
                objective="Require verified Run evidence.",
                workspace=workspace,
                dependencies=("omx-review",),
                source_stage_id="omx-review",
                validator_kind=StrategyValidatorKind.RUN_EVIDENCE,
            ),
            StrategyStage(
                stage_id="finish",
                node_type=StrategyNodeType.FINISH,
                objective="Finish only after all dependencies pass.",
                workspace=workspace,
                dependencies=("validate",),
            ),
        ),
    )

    assert tuple(stage.stage_id for stage in strategy.stages) == (
        "codex-implement",
        "omx-review",
        "validate",
        "finish",
    )


def test_strategy_schema_rejects_forward_dependencies(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(ValidationError, match="non-previous dependencies"):
        StrategyDefinition(
            strategy_id="invalid-forward-edge",
            mission="Reject a graph disguised as a sequence.",
            stages=(
                StrategyStage(
                    stage_id="first",
                    node_type=StrategyNodeType.NATIVE_RUN,
                    provider=ProviderId.CODEX,
                    native_surface="exec",
                    objective="Run first.",
                    workspace=workspace,
                    dependencies=("later",),
                ),
                StrategyStage(
                    stage_id="later",
                    node_type=StrategyNodeType.FINISH,
                    objective="Finish later.",
                    workspace=workspace,
                ),
            ),
        )


def test_strategy_schema_rejects_arbitrary_shell_fields(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StrategyStage.model_validate(
            {
                "stage_id": "unsafe-validator",
                "node_type": "validator",
                "objective": "Do not accept a raw shell string.",
                "workspace": _workspace(tmp_path),
                "validator_kind": "run_evidence",
                "shell": "rm -rf .",
            }
        )


def test_strategy_schema_requires_one_shared_workspace(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()

    with pytest.raises(ValidationError, match="one shared workspace"):
        StrategyDefinition(
            strategy_id="cross-workspace-not-yet-supported",
            mission="Reject unsupported cross-workspace state ownership.",
            stages=(
                StrategyStage(
                    stage_id="run",
                    node_type=StrategyNodeType.NATIVE_RUN,
                    provider=ProviderId.CODEX,
                    native_surface="exec",
                    objective="Run in the first workspace.",
                    workspace=_workspace(tmp_path),
                ),
                StrategyStage(
                    stage_id="finish",
                    node_type=StrategyNodeType.FINISH,
                    objective="Finish elsewhere.",
                    workspace=_workspace(other),
                    dependencies=("run",),
                ),
            ),
        )
