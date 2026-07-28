from __future__ import annotations

import signal
from contextlib import nullcontext
from pathlib import Path

from comx_harness.application.handoff_execution import (
    build_handoff_objective,
    read_handoff_text,
    select_handoff_artifact,
)
from comx_harness.application.run_planning import (
    build_execution_plan,
    build_resume_plan,
    initial_record,
    normalize_request,
)
from comx_harness.application.run_state import (
    persist_missing_process,
    read_record,
    resolve_idempotent_record,
)
from comx_harness.event_normalization import append_run_event
from comx_harness.native_execution import (
    NativeRunExecutor,
    process_liveness,
    signal_process_group,
)
from comx_harness.provider_registry import ProviderRegistry
from comx_harness.run_evidence import collect_run_artifacts
from comx_harness.schemas.artifact_schemas import ArtifactReport
from comx_harness.schemas.execution_schemas import (
    ExecutionPlan,
    ExecutionRequest,
    ResumeRequest,
)
from comx_harness.schemas.handoff_schemas import (
    HandoffExecutionRequest,
    HandoffRecord,
    HandoffRequest,
    HandoffResult,
)
from comx_harness.schemas.lifecycle_schemas import (
    EventReport,
    RunFailure,
    RunRecord,
    RunState,
)
from comx_harness.schemas.provider_schemas import CapabilityReport
from comx_harness.shared.exceptions.harness_exceptions import (
    UnsupportedOperationError,
)
from comx_harness.shared.harness_enums.lifecycle_enums import (
    EventKind,
    ProcessLiveness,
    RunStatus,
)
from comx_harness.storage.harness_storage import open_storage
from comx_harness.storage.time_identity import (
    allocate_handoff_id,
    idempotent_handoff_id,
    utc_timestamp,
)


def _operation_idempotency_key(operation: str, key: str | None) -> str | None:
    if key is None:
        return None
    # Namespacing prevents one caller token from aliasing different mutation types.
    operation_key = f"{operation}:{key}"
    return operation_key


class HarnessService:
    """Controller-neutral application core for Codex and OMX execution."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        executor: NativeRunExecutor | None = None,
    ) -> None:
        self.registry = registry or ProviderRegistry()
        self.executor = executor or NativeRunExecutor()

    def capabilities(self) -> CapabilityReport:
        """Discover installed native providers and supported operations."""
        report = self.registry.discover()
        return report

    def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        """Build an inspectable native plan without writing workspace state."""
        normalized_request = normalize_request(request)
        storage = open_storage(normalized_request.workspace)
        plan = build_execution_plan(
            request=normalized_request,
            registry=self.registry,
            storage=storage,
        )
        return plan

    def run(self, request: ExecutionRequest) -> RunRecord:
        """Execute one task through one native provider."""
        normalized_request = normalize_request(request)
        storage = open_storage(normalized_request.workspace)
        idempotency_key = normalized_request.idempotency_key
        coordination = (
            storage.idempotency.claim(idempotency_key)
            if idempotency_key is not None
            else nullcontext()
        )
        with coordination:
            existing_record = resolve_idempotent_record(
                storage=storage,
                idempotency_key=idempotency_key,
                request=normalized_request,
            )
            if existing_record is not None:
                return existing_record
            plan = build_execution_plan(
                request=normalized_request,
                registry=self.registry,
                storage=storage,
            )
            storage.runs.ensure_run(plan.run_id)
            storage.runs.write_plan(plan)
            storage.runs.write_record(initial_record(plan))
            append_run_event(
                storage,
                run_id=plan.run_id,
                kind=EventKind.LIFECYCLE,
                message="run planned",
            )
            if idempotency_key is not None:
                storage.idempotency.bind(
                    idempotency_key,
                    normalized_request,
                    plan.run_id,
                )
        record = self.executor.execute(plan=plan, storage=storage)
        return record

    def status(self, workspace: str | Path, run_id: str) -> RunState:
        """Read semantic run state and independent process liveness."""
        storage = open_storage(workspace)
        record = read_record(storage, run_id)
        liveness = process_liveness(record)
        if record.status == RunStatus.RUNNING and liveness == ProcessLiveness.MISSING:
            record = persist_missing_process(
                storage=storage,
                record=record,
                failure_message=(
                    "recorded process is no longer running without terminal evidence"
                ),
                event_message="run marked stale after recorded process disappeared",
            )
        state = RunState(record=record, liveness=liveness)
        return state

    def events(self, workspace: str | Path, run_id: str) -> EventReport:
        """Read normalized lifecycle and native JSONL events."""
        storage = open_storage(workspace)
        read_record(storage, run_id)
        report = EventReport(run_id=run_id, events=storage.events.read(run_id))
        return report

    def artifacts(self, workspace: str | Path, run_id: str) -> ArtifactReport:
        """Read verified harness-owned and declared artifacts."""
        storage = open_storage(workspace)
        record = read_record(storage, run_id)
        artifacts = collect_run_artifacts(storage, record, include_declared=True)
        report = ArtifactReport(run_id=run_id, artifacts=artifacts)
        return report

    def cancel(self, workspace: str | Path, run_id: str) -> RunRecord:
        """Request bounded cancellation of the recorded local process."""
        storage = open_storage(workspace)
        record = read_record(storage, run_id)
        if record.status != RunStatus.RUNNING or record.pid is None:
            return record
        try:
            signal_process_group(record.pid, signal.SIGTERM)
        except ProcessLookupError:
            stale_record = persist_missing_process(
                storage=storage,
                record=record,
                failure_message="cancel could not find the recorded process",
                event_message="run marked stale because cancellation found no process",
            )
            return stale_record
        cancelled_record = record.model_copy(
            update={
                "status": RunStatus.CANCELLED,
                "finished_at": utc_timestamp(),
                "failure": RunFailure(
                    code="cancelled",
                    message="cancellation requested by the owning controller",
                    retryable=True,
                ),
            }
        )
        storage.runs.write_record(cancelled_record)
        append_run_event(
            storage,
            run_id=run_id,
            kind=EventKind.LIFECYCLE,
            message="cancellation requested",
        )
        return cancelled_record

    def resume(
        self,
        workspace: str | Path,
        run_id: str,
        objective: str | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> RunRecord:
        """Resume a native session only when its provider id was observed."""
        normalized_workspace = str(Path(workspace).resolve())
        storage = open_storage(normalized_workspace)
        request = ResumeRequest(
            workspace=normalized_workspace,
            run_id=run_id,
            objective=objective,
            idempotency_key=idempotency_key,
        )
        coordination_key = _operation_idempotency_key(
            "resume",
            idempotency_key,
        )
        coordination = (
            storage.idempotency.claim(coordination_key)
            if coordination_key is not None
            else nullcontext()
        )
        with coordination:
            existing_record = resolve_idempotent_record(
                storage=storage,
                idempotency_key=coordination_key,
                request=request,
            )
            if existing_record is not None:
                return existing_record
            source_record = read_record(storage, run_id)
            source_plan = storage.runs.read_plan(run_id)
            session_id = source_record.provider_session_id
            if session_id is None:
                raise UnsupportedOperationError(
                    "resume requires a provider session id observed from native JSONL events"
                )
            resumed_plan = build_resume_plan(
                storage=storage,
                registry=self.registry,
                source_record=source_record,
                source_plan=source_plan,
                objective=objective,
                session_id=session_id,
                idempotency_key=coordination_key,
            )
            storage.runs.ensure_run(resumed_plan.run_id)
            storage.runs.write_plan(resumed_plan)
            storage.runs.write_record(initial_record(resumed_plan))
            append_run_event(
                storage,
                run_id=resumed_plan.run_id,
                kind=EventKind.LIFECYCLE,
                message=f"resume planned from {run_id}",
            )
            if coordination_key is not None:
                storage.idempotency.bind(
                    coordination_key,
                    request,
                    resumed_plan.run_id,
                )
        record = self.executor.execute(plan=resumed_plan, storage=storage)
        return record

    def handoff(
        self,
        workspace: str | Path,
        request: HandoffRequest,
    ) -> HandoffResult:
        """Pass a verified UTF-8 artifact into a different provider."""
        normalized_workspace = str(Path(workspace).resolve())
        storage = open_storage(normalized_workspace)
        normalized_request = HandoffExecutionRequest(
            workspace=normalized_workspace,
            controller_id=request.controller_id,
            origin_run_id=request.origin_run_id,
            target_provider=request.target_provider,
            objective=request.objective,
            artifact_kind=request.artifact_kind,
            timeout_seconds=request.timeout_seconds,
            mutation_allowed=request.mutation_allowed,
            idempotency_key=request.idempotency_key,
            options=request.options,
        )
        coordination_key = _operation_idempotency_key(
            "handoff",
            normalized_request.idempotency_key,
        )
        coordination = (
            storage.idempotency.claim(coordination_key)
            if coordination_key is not None
            else nullcontext()
        )
        with coordination:
            existing_target = resolve_idempotent_record(
                storage=storage,
                idempotency_key=coordination_key,
                request=normalized_request,
            )
            if existing_target is not None and coordination_key is not None:
                existing_handoff = storage.handoffs.read(
                    idempotent_handoff_id(coordination_key)
                )
                result = HandoffResult(
                    handoff=existing_handoff,
                    target_run=existing_target,
                )
                return result
            source_record = read_record(storage, normalized_request.origin_run_id)
            if source_record.provider == normalized_request.target_provider:
                raise UnsupportedOperationError(
                    "same-provider composition should use the provider's native workflow"
                )
            source_artifact = select_handoff_artifact(
                storage=storage,
                source_record=source_record,
                artifact_kind=normalized_request.artifact_kind,
            )
            source_text = read_handoff_text(source_artifact.path)
            target_request = ExecutionRequest(
                controller_id=normalized_request.controller_id,
                provider=normalized_request.target_provider,
                objective=build_handoff_objective(
                    request=normalized_request,
                    source_record=source_record,
                    source_text=source_text,
                    digest=source_artifact.sha256,
                ),
                workspace=normalized_workspace,
                mutation_allowed=normalized_request.mutation_allowed,
                timeout_seconds=normalized_request.timeout_seconds,
                idempotency_key=_operation_idempotency_key(
                    "handoff-target",
                    normalized_request.idempotency_key,
                ),
                options=normalized_request.options,
            )
            target_run = self.run(target_request)
            handoff_id = (
                idempotent_handoff_id(coordination_key)
                if coordination_key is not None
                else allocate_handoff_id()
            )
            handoff = HandoffRecord(
                handoff_id=handoff_id,
                created_at=utc_timestamp(),
                controller_id=normalized_request.controller_id,
                origin_run_id=source_record.run_id,
                source_provider=source_record.provider,
                target_provider=normalized_request.target_provider,
                source_artifact=source_artifact,
                target_run_id=target_run.run_id,
            )
            storage.handoffs.write(handoff)
            if coordination_key is not None:
                storage.idempotency.bind(
                    coordination_key,
                    normalized_request,
                    target_run.run_id,
                )
            result = HandoffResult(handoff=handoff, target_run=target_run)
        return result
