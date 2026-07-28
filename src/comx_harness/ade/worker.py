from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.ade_inspection_schemas import (
    DetachedOperationRecord,
    DetachedOperationRequest,
)
from comx_harness.schemas.execution_schemas import ExecutionRequest, ResumeRequest
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest
from comx_harness.storage.json_file_store import read_json
from comx_harness.storage.time_identity import utc_timestamp

from .detached_operations import (
    serialize_operation_result,
    write_private_operation_model,
)


def execute_operation(
    operation_dir: Path,
    *,
    tools: HarnessTools | None = None,
) -> DetachedOperationRecord:
    request = DetachedOperationRequest.model_validate(
        read_json(operation_dir / "request.json")
    )
    record_path = operation_dir / "operation.json"
    record = _wait_for_launch_record(record_path)
    active_tools = tools or HarnessTools()
    try:
        if request.operation == "run":
            if not isinstance(request.request, ExecutionRequest):
                raise TypeError("run operation requires ExecutionRequest")
            result = active_tools.run(request.request)
        elif request.operation == "resume":
            if not isinstance(request.request, ResumeRequest):
                raise TypeError("resume operation requires ResumeRequest")
            result = active_tools.resume(request.request)
        else:
            if not isinstance(request.request, HandoffExecutionRequest):
                raise TypeError("handoff operation requires HandoffExecutionRequest")
            result = active_tools.handoff(request.request)
        result_path = Path(record.result_path)
        result_path.write_bytes(serialize_operation_result(result))
        result_path.chmod(0o600)
    except Exception as error:
        failed = record.model_copy(
            update={
                "status": "failed",
                "finished_at": utc_timestamp(),
                "error_message": f"{type(error).__name__}: {error}",
            }
        )
        write_private_operation_model(record_path, failed)
        raise
    succeeded = record.model_copy(
        update={"status": "succeeded", "finished_at": utc_timestamp()}
    )
    write_private_operation_model(record_path, succeeded)
    return succeeded


def _wait_for_launch_record(record_path: Path) -> DetachedOperationRecord:
    deadline = time.monotonic() + 5.0
    while True:
        record = DetachedOperationRecord.model_validate(read_json(record_path))
        if record.pid is not None:
            return record
        if time.monotonic() >= deadline:
            raise RuntimeError("detached operation launch metadata was not persisted")
        time.sleep(0.01)


def _operation_dir(state_root: str, operation_id: str) -> Path:
    if (
        not operation_id
        or operation_id in {".", ".."}
        or "/" in operation_id
        or "\\" in operation_id
    ):
        raise ValueError("invalid detached operation id")
    operations_root = (Path(state_root).expanduser().resolve() / "operations").resolve()
    operation_dir = (operations_root / operation_id).resolve()
    if operation_dir.parent != operations_root:
        raise ValueError("invalid detached operation id")
    return operation_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--operation-id", required=True)
    arguments = parser.parse_args()
    operation_dir = _operation_dir(arguments.state_root, arguments.operation_id)
    try:
        execute_operation(operation_dir)
    except Exception as error:
        print(f"detached operation failed: {type(error).__name__}: {error}")
        return 1
    print(f"detached operation completed by pid {os.getpid()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
