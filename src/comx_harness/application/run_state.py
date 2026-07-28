from comx_harness.event_normalization import append_run_event
from comx_harness.schemas.common_schemas import StrictModel
from comx_harness.schemas.lifecycle_schemas import RunFailure, RunRecord
from comx_harness.shared.exceptions.harness_exceptions import RunNotFoundError
from comx_harness.shared.exceptions.idempotency_exceptions import (
    IdempotencyConflictError,
)
from comx_harness.shared.harness_enums.lifecycle_enums import EventKind, RunStatus
from comx_harness.storage.harness_storage import HarnessStorage
from comx_harness.storage.idempotency_store import idempotency_request_sha256
from comx_harness.storage.time_identity import utc_timestamp


def read_record(storage: HarnessStorage, run_id: str) -> RunRecord:
    try:
        record = storage.runs.read_record(run_id)
    except FileNotFoundError as error:
        raise RunNotFoundError(f"run not found: {run_id}") from error
    return record


def resolve_idempotent_record(
    *,
    storage: HarnessStorage,
    idempotency_key: str | None,
    request: StrictModel,
) -> RunRecord | None:
    if idempotency_key is None:
        return None
    binding = storage.idempotency.resolve(idempotency_key)
    if binding is None:
        return None
    request_sha256 = idempotency_request_sha256(request)
    if binding.request_sha256 != request_sha256:
        raise IdempotencyConflictError(
            "idempotency key is already bound to a different operation request"
        )
    record = read_record(storage, binding.run_id)
    return record


def persist_missing_process(
    *,
    storage: HarnessStorage,
    record: RunRecord,
    failure_message: str,
    event_message: str,
) -> RunRecord:
    stale_record = record.model_copy(
        update={
            "status": RunStatus.STALE,
            "finished_at": utc_timestamp(),
            "failure": RunFailure(
                code="process_missing",
                message=failure_message,
                retryable=True,
            ),
        }
    )
    storage.runs.write_record(stale_record)
    append_run_event(
        storage,
        run_id=record.run_id,
        kind=EventKind.LIFECYCLE,
        message=event_message,
    )
    return stale_record
