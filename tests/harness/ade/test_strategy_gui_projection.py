from pathlib import Path

from comx_harness.ade.tk_refresh import (
    _stage_evidence_label,
    _stage_surface_label,
    _strategy_evidence_label,
)
from comx_harness.schemas.strategy_schemas import (
    StrategyDefinition,
    StrategyEvidence,
    StrategyRecord,
    StrategyStage,
    StrategyStageRecord,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    StrategyNodeType,
    StrategyStageStatus,
    StrategyStatus,
)


def _record(workspace: Path) -> StrategyRecord:
    definition = StrategyDefinition(
        strategy_id="gui-observation",
        mission="Show only durable runtime facts.",
        stages=(
            StrategyStage(
                stage_id="codex-review",
                node_type=StrategyNodeType.NATIVE_RUN,
                provider=ProviderId.CODEX,
                native_surface="exec",
                objective="Read the workspace.",
                workspace=str(workspace),
            ),
            StrategyStage(
                stage_id="finish",
                node_type=StrategyNodeType.FINISH,
                objective="Finish after review.",
                workspace=str(workspace),
                dependencies=("codex-review",),
            ),
        ),
    )
    return StrategyRecord(
        definition=definition,
        status=StrategyStatus.RUNNING,
        created_at="2026-07-29T00:00:00Z",
        updated_at="2026-07-29T00:00:01Z",
        current_stage_id="codex-review",
        stages=(
            StrategyStageRecord(
                stage_id="codex-review",
                node_type=StrategyNodeType.NATIVE_RUN,
                status=StrategyStageStatus.SUCCEEDED,
                provider=ProviderId.CODEX,
                run_id="run-observed",
                attempts=1,
                evidence=(
                    StrategyEvidence(
                        kind="process_exit",
                        passed=True,
                        detail="native process exit code is 0",
                    ),
                    StrategyEvidence(
                        kind="required_artifacts",
                        passed=True,
                        detail="artifacts have digest",
                        digest="a" * 64,
                    ),
                ),
            ),
            StrategyStageRecord(
                stage_id="finish",
                node_type=StrategyNodeType.FINISH,
                status=StrategyStageStatus.PENDING,
            ),
        ),
    )


def test_strategy_gui_labels_use_only_observed_runtime_state(tmp_path: Path) -> None:
    record = _record(tmp_path)
    run_definition = record.definition.stages[0]
    finish_definition = record.definition.stages[1]
    run_stage = record.stages[0]
    finish_stage = record.stages[1]

    assert _stage_surface_label(run_definition) == "exec"
    assert _stage_surface_label(finish_definition) == "finish"
    assert _stage_evidence_label(run_stage) == "2 passed"
    assert _stage_evidence_label(finish_stage) == "no evidence yet"
    assert _strategy_evidence_label(record) == "2/2 evidence passed"


def test_strategy_gui_exposes_failure_without_inventing_provider_state(
    tmp_path: Path,
) -> None:
    record = _record(tmp_path)
    failed = record.stages[1].model_copy(
        update={
            "status": StrategyStageStatus.FAILED,
            "failure": "structured blocker count is unavailable",
        }
    )

    assert failed.provider is None
    assert failed.run_id is None
    assert _stage_evidence_label(failed) == "structured blocker count is unavailable"
