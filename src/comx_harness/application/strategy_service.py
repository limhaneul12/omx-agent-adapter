from __future__ import annotations

from pathlib import Path

from comx_harness.application.capability_matrix import (
    capability_support,
    resolve_capability_matrix,
)
from comx_harness.application.strategy_stage_execution import StrategyStageExecutor
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.capability_matrix_schemas import CapabilityMatrixReport
from comx_harness.schemas.execution_schemas import RunReference
from comx_harness.schemas.strategy_schemas import (
    StrategyArtifact,
    StrategyArtifactReport,
    StrategyDefinition,
    StrategyEvent,
    StrategyEventReport,
    StrategyRecord,
    StrategyStage,
    StrategyStageRecord,
    StrategyValidationIssue,
    StrategyValidationReport,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    CapabilitySupport,
    NativeCapability,
    StrategyEventKind,
    StrategyFailureAction,
    StrategyNodeType,
    StrategyStageStatus,
    StrategyStatus,
)
from comx_harness.storage.strategy_store import StrategyStore
from comx_harness.storage.time_identity import utc_timestamp
from comx_harness.storage.workspace_layout import WorkspaceLayout


class StrategyService:
    """Coordinate a bounded Strategy over the existing Run lifecycle."""

    def __init__(self, tools: HarnessTools | None = None) -> None:
        self.tools = tools or HarnessTools()
        self._stage_executor = StrategyStageExecutor(self.tools)

    def capabilities(self) -> CapabilityMatrixReport:
        return resolve_capability_matrix(self.tools.capabilities())

    def validate(self, definition: StrategyDefinition) -> StrategyValidationReport:
        matrix = self.capabilities()
        issues: list[StrategyValidationIssue] = []
        for stage in definition.stages:
            issues.extend(self._stage_validation_issues(stage, matrix))
        return StrategyValidationReport(
            strategy_id=definition.strategy_id,
            valid=not issues,
            issues=tuple(issues),
        )

    def execute(self, definition: StrategyDefinition) -> StrategyRecord:
        validation = self.validate(definition)
        if not validation.valid:
            details = "; ".join(issue.detail for issue in validation.issues)
            raise ValueError(f"strategy validation failed: {details}")
        store = self._store(definition.stages[0].workspace)
        existing = self._existing_record(store, definition)
        if existing is not None:
            return existing

        timestamp = utc_timestamp()
        record = StrategyRecord(
            definition=definition,
            status=StrategyStatus.PENDING,
            created_at=timestamp,
            updated_at=timestamp,
            stages=tuple(
                StrategyStageRecord(
                    stage_id=stage.stage_id,
                    node_type=stage.node_type,
                    status=StrategyStageStatus.PENDING,
                    provider=stage.provider,
                )
                for stage in definition.stages
            ),
        )
        record = store.write(record)
        self._append_event(store, record, StrategyEventKind.STRATEGY, "created")
        record = self._update_strategy(
            store,
            record,
            status=StrategyStatus.RUNNING,
        )
        self._append_event(store, record, StrategyEventKind.STRATEGY, "started")

        for stage in definition.stages:
            record = self._stage_executor.execute(store, record, stage)
            stage_record = self._stage_record(record, stage.stage_id)
            if (
                StrategyStageStatus(stage_record.status) == StrategyStageStatus.FAILED
                and StrategyFailureAction(stage.failure_policy.action)
                == StrategyFailureAction.STOP
            ):
                record = self._update_strategy(
                    store,
                    record,
                    status=StrategyStatus.FAILED,
                    current_stage_id=None,
                )
                self._append_event(
                    store,
                    record,
                    StrategyEventKind.STRATEGY,
                    "failed",
                    stage_id=stage.stage_id,
                )
                return record

        final_status = (
            StrategyStatus.SUCCEEDED
            if StrategyStageStatus(record.stages[-1].status)
            == StrategyStageStatus.SUCCEEDED
            else StrategyStatus.FAILED
        )
        record = self._update_strategy(
            store,
            record,
            status=final_status,
            current_stage_id=None,
        )
        self._append_event(
            store,
            record,
            StrategyEventKind.STRATEGY,
            str(final_status),
        )
        return record

    def status(self, workspace: str, strategy_id: str) -> StrategyRecord:
        return self._store(workspace).read(strategy_id)

    def events(self, workspace: str, strategy_id: str) -> StrategyEventReport:
        events = self._store(workspace).read_events(strategy_id)
        return StrategyEventReport(strategy_id=strategy_id, events=events)

    def artifacts(self, workspace: str, strategy_id: str) -> StrategyArtifactReport:
        record = self.status(workspace, strategy_id)
        artifacts: list[StrategyArtifact] = []
        for stage in record.stages:
            if stage.run_id is None:
                continue
            report = self.tools.artifacts(
                RunReference(workspace=workspace, run_id=stage.run_id)
            )
            artifacts.extend(
                StrategyArtifact(
                    stage_id=stage.stage_id,
                    run_id=stage.run_id,
                    artifact=artifact,
                )
                for artifact in report.artifacts
            )
        return StrategyArtifactReport(
            strategy_id=strategy_id,
            artifacts=tuple(artifacts),
        )

    def _stage_validation_issues(
        self,
        stage: StrategyStage,
        matrix: CapabilityMatrixReport,
    ) -> tuple[StrategyValidationIssue, ...]:
        issues: list[StrategyValidationIssue] = []
        node_type = StrategyNodeType(stage.node_type)
        if node_type == StrategyNodeType.NATIVE_RUN:
            if stage.workflow is not None:
                issues.append(
                    StrategyValidationIssue(
                        stage_id=stage.stage_id,
                        code="workflow_execution_not_implemented",
                        detail=(
                            "The first vertical slice records native workflow "
                            "capabilities but executes only the native exec surface."
                        ),
                    )
                )
            if stage.native_surface not in {None, "exec"}:
                issues.append(
                    StrategyValidationIssue(
                        stage_id=stage.stage_id,
                        code="native_surface_unsupported",
                        detail=(
                            f"native surface {stage.native_surface!r} is not executable "
                            "by strategy-definition.v1"
                        ),
                    )
                )
        requirements = list(stage.capability_requirements)
        if node_type == StrategyNodeType.NATIVE_RESUME:
            requirements.append(NativeCapability.RESUME)
        elif node_type == StrategyNodeType.HANDOFF:
            requirements.append(NativeCapability.ARTIFACTS)
        if stage.provider is not None:
            provider = ProviderId(stage.provider)
            for requirement in dict.fromkeys(requirements):
                support = capability_support(matrix, provider, requirement)
                if support in {
                    CapabilitySupport.UNSUPPORTED,
                    CapabilitySupport.UNKNOWN,
                }:
                    issues.append(
                        StrategyValidationIssue(
                            stage_id=stage.stage_id,
                            code="capability_requirement_unsatisfied",
                            detail=f"{provider} capability {requirement} is {support}",
                        )
                    )
        return tuple(issues)

    def _update_strategy(
        self,
        store: StrategyStore,
        record: StrategyRecord,
        *,
        status: StrategyStatus,
        current_stage_id: str | None = None,
    ) -> StrategyRecord:
        updated = record.model_copy(
            update={
                "status": status,
                "updated_at": utc_timestamp(),
                "current_stage_id": current_stage_id,
            }
        )
        return store.write(updated)

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

    def _existing_record(
        self,
        store: StrategyStore,
        definition: StrategyDefinition,
    ) -> StrategyRecord | None:
        try:
            existing = store.read(definition.strategy_id)
        except FileNotFoundError:
            return None
        if existing.definition != definition:
            raise ValueError(
                f"strategy_id {definition.strategy_id!r} already has another definition"
            )
        return existing

    def _stage_record(
        self,
        record: StrategyRecord,
        stage_id: str,
    ) -> StrategyStageRecord:
        for stage in record.stages:
            if stage.stage_id == stage_id:
                return stage
        raise KeyError(stage_id)

    def _store(self, workspace: str) -> StrategyStore:
        path = Path(workspace).expanduser().resolve()
        return StrategyStore(WorkspaceLayout.from_workspace(path))
