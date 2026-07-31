from __future__ import annotations

from comx_harness.application.strategy_evidence import StrategyEvidenceEvaluator
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.execution_schemas import ExecutionRequest, ResumeRequest
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest
from comx_harness.schemas.strategy_schemas import (
    StrategyEvent,
    StrategyEvidence,
    StrategyRecord,
    StrategyStage,
    StrategyStageRecord,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    StrategyEventKind,
    StrategyNodeType,
    StrategyRunCondition,
    StrategyStageStatus,
)
from comx_harness.storage.strategy_store import StrategyStore
from comx_harness.storage.time_identity import utc_timestamp


class StrategyStageExecutor:
    """Execute one bounded Stage by delegating to existing HarnessTools operations."""

    def __init__(self, tools: HarnessTools) -> None:
        self._tools = tools
        self._evidence = StrategyEvidenceEvaluator(tools)

    def execute(
        self,
        store: StrategyStore,
        record: StrategyRecord,
        stage: StrategyStage,
    ) -> StrategyRecord:
        if not self._condition_satisfied(record, stage):
            failure = f"run condition {stage.run_condition} was not satisfied"
            skipped = StrategyStageRecord(
                stage_id=stage.stage_id,
                node_type=stage.node_type,
                status=StrategyStageStatus.SKIPPED,
                provider=stage.provider,
                failure=failure,
            )
            record = self._replace_stage(store, record, skipped)
            self._append_event(
                store,
                record,
                StrategyEventKind.STAGE,
                "skipped",
                stage_id=stage.stage_id,
            )
            return record

        last_failure = "stage did not execute"
        for attempt in range(1, stage.failure_policy.max_attempts + 1):
            started_at = utc_timestamp()
            running = StrategyStageRecord(
                stage_id=stage.stage_id,
                node_type=stage.node_type,
                status=StrategyStageStatus.RUNNING,
                provider=stage.provider,
                attempts=attempt,
                started_at=started_at,
            )
            record = self._replace_stage(
                store,
                record,
                running,
                current_stage_id=stage.stage_id,
            )
            self._append_event(
                store,
                record,
                StrategyEventKind.STAGE,
                f"attempt {attempt} started",
                stage_id=stage.stage_id,
            )
            run_id, handoff_id, evidence, last_failure = self._attempt(
                record,
                stage,
            )
            passed = bool(evidence) and all(item.passed for item in evidence)
            completed = StrategyStageRecord(
                stage_id=stage.stage_id,
                node_type=stage.node_type,
                status=(
                    StrategyStageStatus.SUCCEEDED
                    if passed
                    else StrategyStageStatus.FAILED
                ),
                provider=stage.provider,
                run_id=run_id,
                handoff_id=handoff_id,
                attempts=attempt,
                started_at=started_at,
                completed_at=utc_timestamp(),
                evidence=evidence,
                failure=None if passed else last_failure,
            )
            record = self._replace_stage(store, record, completed)
            self._append_evidence(store, record, stage, evidence)
            if passed:
                self._append_event(
                    store,
                    record,
                    StrategyEventKind.STAGE,
                    "succeeded",
                    stage_id=stage.stage_id,
                )
                return record
        self._append_event(
            store,
            record,
            StrategyEventKind.STAGE,
            "failed",
            stage_id=stage.stage_id,
        )
        return record

    def _attempt(
        self,
        record: StrategyRecord,
        stage: StrategyStage,
    ) -> tuple[
        str | None,
        str | None,
        tuple[StrategyEvidence, ...],
        str,
    ]:
        try:
            run_id, handoff_id, evidence = self._execute_stage(record, stage)
        except (FileNotFoundError, KeyError, OSError, ValueError) as error:
            failure = str(error) or type(error).__name__
            return (
                None,
                None,
                (
                    StrategyEvidence(
                        kind="runtime_error",
                        passed=False,
                        detail=failure,
                    ),
                ),
                failure,
            )
        passed = bool(evidence) and all(item.passed for item in evidence)
        failure = "" if passed else "completion criteria were not satisfied"
        return run_id, handoff_id, evidence, failure

    def _execute_stage(
        self,
        record: StrategyRecord,
        stage: StrategyStage,
    ) -> tuple[str | None, str | None, tuple[StrategyEvidence, ...]]:
        node_type = StrategyNodeType(stage.node_type)
        if node_type == StrategyNodeType.NATIVE_RUN:
            run = self._tools.run(
                ExecutionRequest(
                    controller_id=record.definition.controller_id,
                    provider=ProviderId(stage.provider),
                    objective=stage.objective,
                    workspace=stage.workspace,
                    mutation_allowed=stage.mutation_allowed,
                    timeout_seconds=stage.timeout_seconds,
                    idempotency_key=(
                        f"strategy:{record.definition.strategy_id}:{stage.stage_id}"
                    ),
                    expected_artifacts=stage.expected_artifacts,
                    options=stage.options,
                )
            )
            return run.run_id, None, self._evidence.run_evidence(stage, run)
        if node_type == StrategyNodeType.NATIVE_RESUME:
            source_run_id = self._source_run_id(record, stage)
            run = self._tools.resume(
                ResumeRequest(
                    workspace=stage.workspace,
                    run_id=source_run_id,
                    objective=stage.objective,
                    idempotency_key=(
                        f"strategy:{record.definition.strategy_id}:{stage.stage_id}"
                    ),
                )
            )
            return run.run_id, None, self._evidence.run_evidence(stage, run)
        if node_type == StrategyNodeType.HANDOFF:
            return self._handoff(record, stage)
        if node_type == StrategyNodeType.VALIDATOR:
            return None, None, self._evidence.validator_evidence(record, stage)
        if node_type == StrategyNodeType.FINISH:
            passed = self._condition_satisfied(record, stage)
            return (
                None,
                None,
                (
                    StrategyEvidence(
                        kind="finish_dependencies",
                        passed=passed,
                        detail=(
                            "finish run condition is satisfied"
                            if passed
                            else "finish dependencies are unresolved"
                        ),
                    ),
                ),
            )
        raise AssertionError(f"unhandled strategy node: {node_type}")

    def _handoff(
        self,
        record: StrategyRecord,
        stage: StrategyStage,
    ) -> tuple[str, str, tuple[StrategyEvidence, ...]]:
        source_run_id = self._source_run_id(record, stage)
        result = self._tools.handoff(
            HandoffExecutionRequest(
                controller_id=record.definition.controller_id,
                origin_run_id=source_run_id,
                target_provider=ProviderId(stage.provider),
                objective=stage.objective,
                artifact_kind=(
                    stage.input_artifacts[0] if stage.input_artifacts else "result"
                ),
                timeout_seconds=stage.timeout_seconds,
                mutation_allowed=stage.mutation_allowed,
                idempotency_key=(
                    f"strategy:{record.definition.strategy_id}:{stage.stage_id}"
                ),
                options=stage.options,
                workspace=stage.workspace,
            )
        )
        return (
            result.target_run.run_id,
            result.handoff.handoff_id,
            self._evidence.run_evidence(stage, result.target_run),
        )

    def _source_run_id(self, record: StrategyRecord, stage: StrategyStage) -> str:
        if stage.source_stage_id is None:
            raise ValueError(f"stage {stage.stage_id} has no source_stage_id")
        source = self._stage_record(record, stage.source_stage_id)
        if source.run_id is None:
            raise ValueError(
                f"source stage {stage.source_stage_id} has no observed run_id"
            )
        return source.run_id

    def _condition_satisfied(
        self,
        record: StrategyRecord,
        stage: StrategyStage,
    ) -> bool:
        if not stage.dependencies:
            return True
        statuses = tuple(
            StrategyStageStatus(self._stage_record(record, dependency).status)
            for dependency in stage.dependencies
        )
        condition = StrategyRunCondition(stage.run_condition)
        if condition == StrategyRunCondition.ALL_DEPENDENCIES_SUCCEEDED:
            return all(status == StrategyStageStatus.SUCCEEDED for status in statuses)
        if condition == StrategyRunCondition.ANY_DEPENDENCY_SUCCEEDED:
            return any(status == StrategyStageStatus.SUCCEEDED for status in statuses)
        if condition == StrategyRunCondition.ANY_DEPENDENCY_FAILED:
            return any(status == StrategyStageStatus.FAILED for status in statuses)
        raise AssertionError(f"unhandled Strategy run condition: {condition}")

    def _replace_stage(
        self,
        store: StrategyStore,
        record: StrategyRecord,
        replacement: StrategyStageRecord,
        *,
        current_stage_id: str | None = None,
    ) -> StrategyRecord:
        stages = tuple(
            replacement if stage.stage_id == replacement.stage_id else stage
            for stage in record.stages
        )
        updated = record.model_copy(
            update={
                "stages": stages,
                "updated_at": utc_timestamp(),
                "current_stage_id": current_stage_id,
            }
        )
        return store.write(updated)

    def _append_evidence(
        self,
        store: StrategyStore,
        record: StrategyRecord,
        stage: StrategyStage,
        evidence: tuple[StrategyEvidence, ...],
    ) -> None:
        for item in evidence:
            self._append_event(
                store,
                record,
                StrategyEventKind.EVIDENCE,
                item.detail,
                stage_id=stage.stage_id,
            )

    def _append_event(
        self,
        store: StrategyStore,
        record: StrategyRecord,
        kind: StrategyEventKind,
        message: str,
        *,
        stage_id: str | None = None,
    ) -> StrategyEvent:
        sequence = len(store.read_events(record.definition.strategy_id)) + 1
        return store.append_event(
            StrategyEvent(
                strategy_id=record.definition.strategy_id,
                sequence=sequence,
                timestamp=utc_timestamp(),
                kind=kind,
                message=message,
                stage_id=stage_id,
            )
        )

    def _stage_record(
        self,
        record: StrategyRecord,
        stage_id: str,
    ) -> StrategyStageRecord:
        for stage in record.stages:
            if stage.stage_id == stage_id:
                return stage
        raise KeyError(stage_id)
