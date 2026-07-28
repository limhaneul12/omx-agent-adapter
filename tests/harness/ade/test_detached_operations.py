from __future__ import annotations

import time
from pathlib import Path

import orjson
import pytest
from comx_harness.ade.detached_operations import DetachedOperationService
from comx_harness.ade.worker import execute_operation
from comx_harness.schemas.ade_inspection_schemas import DetachedOperationRequest
from comx_harness.schemas.execution_schemas import ExecutionRequest, ResumeRequest
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.shared.harness_enums.lifecycle_enums import RunStatus
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from pydantic import ValidationError


class _FakeProcess:
    pid = 7654


class _FakeTools:
    def run(self, request: ExecutionRequest) -> RunRecord:
        return RunRecord(
            run_id="run-detached",
            owner_controller_id=request.controller_id,
            provider=request.provider,
            objective=request.objective,
            status=RunStatus.SUCCEEDED,
            plan_path=f"{request.workspace}/plan.json",
            started_at="2026-07-28T00:00:00Z",
            finished_at="2026-07-28T00:00:01Z",
            exit_code=0,
        )


def test_start_run_serializes_request_and_spawns_detached_worker(
    tmp_path: Path,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def launcher(
        argv: tuple[str, ...],
        **kwargs: object,
    ) -> _FakeProcess:
        calls.append((argv, kwargs))
        return _FakeProcess()

    service = DetachedOperationService(
        tmp_path / "ade-state",
        launcher=launcher,
        python_executable="/test/python",
    )
    request = ExecutionRequest(
        provider=ProviderId.CODEX,
        objective="Inspect safely",
        workspace=str(tmp_path),
    )

    record = service.start_run(request)

    assert record.status == "running"
    assert record.pid == 7654
    assert service.read(record.operation_id) == record
    payload = orjson.loads(Path(record.request_path).read_bytes())
    assert payload["operation"] == "run"
    assert payload["request"]["objective"] == "Inspect safely"
    argv, kwargs = calls[0]
    assert argv[:3] == (
        "/test/python",
        "-m",
        "comx_harness.ade.worker",
    )
    assert kwargs["start_new_session"] is True
    assert kwargs["close_fds"] is True
    assert "shell" not in kwargs
    operation_directory = Path(record.request_path).parent
    assert operation_directory.stat().st_mode & 0o777 == 0o700
    assert Path(record.request_path).stat().st_mode & 0o777 == 0o600
    assert Path(record.stdout_path).stat().st_mode & 0o777 == 0o600
    assert Path(record.stderr_path).stat().st_mode & 0o777 == 0o600


def test_worker_calls_only_harness_tools_operation_and_persists_result(
    tmp_path: Path,
) -> None:
    service = DetachedOperationService(
        tmp_path / "ade-state",
        launcher=lambda *args, **kwargs: _FakeProcess(),
    )
    record = service.start_run(
        ExecutionRequest(
            provider=ProviderId.CODEX,
            objective="Inspect safely",
            workspace=str(tmp_path),
        )
    )

    finished = execute_operation(
        Path(record.request_path).parent,
        tools=_FakeTools(),  # type: ignore[arg-type]
    )

    assert finished.status == "succeeded"
    assert finished.finished_at is not None
    result = orjson.loads(Path(finished.result_path).read_bytes())
    assert result["run_id"] == "run-detached"
    assert result["status"] == "succeeded"


def test_detached_request_rejects_mismatched_operation_contract(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="wrong request contract"):
        DetachedOperationRequest(
            operation="run",
            request=ResumeRequest(workspace=str(tmp_path), run_id="run-source"),
        )


def test_worker_failure_is_durable(tmp_path: Path) -> None:
    class FailingTools(_FakeTools):
        def run(self, request: ExecutionRequest) -> RunRecord:
            del request
            raise RuntimeError("provider unavailable")

    service = DetachedOperationService(
        tmp_path / "ade-state",
        launcher=lambda *args, **kwargs: _FakeProcess(),
    )
    record = service.start_run(
        ExecutionRequest(
            provider=ProviderId.CODEX,
            objective="Inspect safely",
            workspace=str(tmp_path),
        )
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        execute_operation(
            Path(record.request_path).parent,
            tools=FailingTools(),  # type: ignore[arg-type]
        )

    failed = service.read(record.operation_id)
    assert failed.status == "failed"
    assert failed.error_message == "RuntimeError: provider unavailable"
    assert failed.finished_at is not None


def test_detached_worker_launch_failure_is_durable(tmp_path: Path) -> None:
    def failing_launcher(*args: object, **kwargs: object) -> _FakeProcess:
        del args, kwargs
        raise FileNotFoundError("python unavailable")

    service = DetachedOperationService(
        tmp_path / "ade-state",
        launcher=failing_launcher,
    )

    failed = service.start_run(
        ExecutionRequest(
            provider=ProviderId.CODEX,
            objective="Inspect safely",
            workspace=str(tmp_path),
        )
    )

    assert failed.status == "failed"
    assert failed.pid is None
    assert failed.error_message == "FileNotFoundError: python unavailable"
    assert service.read(failed.operation_id) == failed


def test_real_detached_worker_survives_launcher_scope_and_finishes(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    del fake_provider_path
    service = DetachedOperationService(tmp_path / "ade-state")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    launched = service.start_run(
        ExecutionRequest(
            provider=ProviderId.CODEX,
            objective="Complete outside the ADE process session",
            workspace=str(workspace),
        )
    )

    deadline = time.monotonic() + 10.0
    current = launched
    while current.status == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        current = service.read(launched.operation_id)

    assert current.status == "succeeded"
    assert Path(current.result_path).is_file()
    result = orjson.loads(Path(current.result_path).read_bytes())
    assert result["status"] == "succeeded"


def test_detached_operation_records_are_listed_newest_first(tmp_path: Path) -> None:
    service = DetachedOperationService(
        tmp_path / "ade-state",
        launcher=lambda *args, **kwargs: _FakeProcess(),
    )
    first = service.start_run(
        ExecutionRequest(
            provider=ProviderId.CODEX,
            objective="First operation",
            workspace=str(tmp_path),
        )
    )
    second = service.start_run(
        ExecutionRequest(
            provider=ProviderId.CODEX,
            objective="Second operation",
            workspace=str(tmp_path),
        )
    )

    records = service.list_records()

    assert {record.operation_id for record in records} == {
        first.operation_id,
        second.operation_id,
    }
    assert records == tuple(
        sorted(records, key=lambda record: record.created_at, reverse=True)
    )
