from pathlib import Path

from comx_harness.provider_registry import ProviderRegistry
from comx_harness.schemas.execution_schemas import ExecutionPlan, ExecutionRequest
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.shared.exceptions.harness_exceptions import HarnessError
from comx_harness.shared.harness_enums.lifecycle_enums import RunStatus
from comx_harness.storage.harness_storage import HarnessStorage
from comx_harness.storage.time_identity import (
    allocate_run_id,
    idempotent_run_id,
    utc_timestamp,
)


def normalize_request(request: ExecutionRequest) -> ExecutionRequest:
    workspace = Path(request.workspace).resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise HarnessError(
            f"workspace does not exist or is not a directory: {workspace}"
        )
    normalized_request = request.model_copy(update={"workspace": str(workspace)})
    return normalized_request


def build_execution_plan(
    *,
    request: ExecutionRequest,
    registry: ProviderRegistry,
    storage: HarnessStorage,
) -> ExecutionPlan:
    provider = registry.get(request.provider)
    run_id = (
        idempotent_run_id(request.idempotency_key)
        if request.idempotency_key is not None
        else allocate_run_id()
    )
    paths = storage.layout.run_paths(run_id)
    argv = provider.build_run_argv(request, paths.result)
    plan = ExecutionPlan(
        run_id=run_id,
        created_at=utc_timestamp(),
        request=request,
        provider=request.provider,
        argv=argv,
        cwd=request.workspace,
        run_dir=str(paths.directory),
        result_path=str(paths.result),
        stdout_path=str(paths.stdout),
        stderr_path=str(paths.stderr),
        events_path=str(paths.events),
        supports_cancel=True,
        supports_resume=True,
    )
    return plan


def build_resume_plan(
    *,
    storage: HarnessStorage,
    registry: ProviderRegistry,
    source_record: RunRecord,
    source_plan: ExecutionPlan,
    objective: str | None,
    session_id: str,
    idempotency_key: str | None,
) -> ExecutionPlan:
    provider = registry.get(source_record.provider)
    run_id = (
        idempotent_run_id(idempotency_key)
        if idempotency_key is not None
        else allocate_run_id()
    )
    resumed_objective = (
        objective or "Continue the previous task and finish its objective."
    )
    paths = storage.layout.run_paths(run_id)
    argv = provider.build_resume_argv(
        source_plan,
        session_id,
        resumed_objective,
        paths.result,
    )
    resumed_request = source_plan.request.model_copy(
        update={"objective": resumed_objective, "idempotency_key": None}
    )
    plan = ExecutionPlan(
        run_id=run_id,
        created_at=utc_timestamp(),
        request=resumed_request,
        provider=source_record.provider,
        argv=argv,
        cwd=source_plan.cwd,
        run_dir=str(paths.directory),
        result_path=str(paths.result),
        stdout_path=str(paths.stdout),
        stderr_path=str(paths.stderr),
        events_path=str(paths.events),
        supports_cancel=True,
        supports_resume=True,
        parent_run_id=source_record.run_id,
        resume_session_id=session_id,
    )
    return plan


def initial_record(plan: ExecutionPlan) -> RunRecord:
    record = RunRecord(
        run_id=plan.run_id,
        owner_controller_id=plan.request.controller_id,
        provider=plan.provider,
        objective=plan.request.objective,
        status=RunStatus.PLANNED,
        plan_path=str(Path(plan.run_dir) / "plan.json"),
        parent_run_id=plan.parent_run_id,
    )
    return record
