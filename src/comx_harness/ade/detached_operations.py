from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import orjson
from comx_harness.schemas.ade_inspection_schemas import (
    DetachedOperationRecord,
    DetachedOperationRequest,
)
from comx_harness.schemas.execution_schemas import ExecutionRequest, ResumeRequest
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest
from comx_harness.storage.json_file_store import read_json, write_model
from comx_harness.storage.time_identity import compact_timestamp, utc_timestamp
from pydantic import BaseModel

DetachedLauncher = Callable[..., subprocess.Popen[bytes]]


class DetachedOperationService:
    """Launch run-like HarnessTools calls outside the ADE process session."""

    def __init__(
        self,
        state_root: str | Path,
        *,
        launcher: DetachedLauncher = subprocess.Popen,
        python_executable: str = sys.executable,
    ) -> None:
        self._state_root = Path(state_root).expanduser().resolve()
        self._launcher = launcher
        self._python_executable = python_executable

    def start_run(self, request: ExecutionRequest) -> DetachedOperationRecord:
        return self._start(DetachedOperationRequest(operation="run", request=request))

    def start_resume(self, request: ResumeRequest) -> DetachedOperationRecord:
        return self._start(
            DetachedOperationRequest(operation="resume", request=request)
        )

    def start_handoff(
        self,
        request: HandoffExecutionRequest,
    ) -> DetachedOperationRecord:
        return self._start(
            DetachedOperationRequest(operation="handoff", request=request)
        )

    def read(self, operation_id: str) -> DetachedOperationRecord:
        record_path = self._operation_dir(operation_id) / "operation.json"
        payload = read_json(record_path)
        return DetachedOperationRecord.model_validate(payload)

    def _start(
        self,
        request: DetachedOperationRequest,
    ) -> DetachedOperationRecord:
        operation_id = f"ade-operation-{compact_timestamp()}-{uuid4().hex[:8]}"
        operation_dir = self._operation_dir(operation_id)
        operation_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        request_path = operation_dir / "request.json"
        record_path = operation_dir / "operation.json"
        result_path = operation_dir / "result.json"
        stdout_path = operation_dir / "stdout.log"
        stderr_path = operation_dir / "stderr.log"
        write_private_operation_model(request_path, request)
        queued = DetachedOperationRecord(
            operation_id=operation_id,
            operation=request.operation,
            status="queued",
            created_at=utc_timestamp(),
            request_path=str(request_path),
            result_path=str(result_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
        write_private_operation_model(record_path, queued)
        stdout_path.touch(mode=0o600, exist_ok=False)
        stderr_path.touch(mode=0o600, exist_ok=False)
        try:
            with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
                process = self._launcher(
                    (
                        self._python_executable,
                        "-m",
                        "comx_harness.ade.worker",
                        "--state-root",
                        str(self._state_root),
                        "--operation-id",
                        operation_id,
                    ),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                    close_fds=True,
                )
        except OSError as error:
            failed = queued.model_copy(
                update={
                    "status": "failed",
                    "finished_at": utc_timestamp(),
                    "error_message": f"{type(error).__name__}: {error}",
                }
            )
            write_model(record_path, failed)
            return failed
        running = queued.model_copy(
            update={
                "status": "running",
                "started_at": utc_timestamp(),
                "pid": process.pid,
            }
        )
        write_private_operation_model(record_path, running)
        return running

    def _operation_dir(self, operation_id: str) -> Path:
        if (
            not operation_id
            or operation_id in {".", ".."}
            or "/" in operation_id
            or "\\" in operation_id
        ):
            raise ValueError("invalid detached operation id")
        path = (self._state_root / "operations" / operation_id).resolve()
        operations_root = (self._state_root / "operations").resolve()
        if path.parent != operations_root:
            raise ValueError("invalid detached operation id")
        return path


def serialize_operation_result(result: object) -> bytes:
    model_dump = getattr(result, "model_dump", None)
    if not callable(model_dump):
        raise TypeError("HarnessTools operation returned a non-model result")
    return orjson.dumps(
        model_dump(mode="json"),
        option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
    )


def write_private_operation_model(path: Path, model: BaseModel) -> None:
    """Persist worker metadata with single-user filesystem permissions."""
    write_model(path, model)
    # Requests can contain unpublished objectives and verified handoff content.
    path.chmod(0o600)
