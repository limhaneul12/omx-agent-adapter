from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import pytest
from comx_harness.application.harness_service import HarnessService
from comx_harness.schemas.execution_schemas import ExecutionRequest, RunOptions
from comx_harness.schemas.handoff_schemas import HandoffRequest, HandoffResult
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.shared.exceptions.harness_exceptions import UnsupportedOperationError
from comx_harness.shared.exceptions.idempotency_exceptions import (
    IdempotencyConflictError,
)
from comx_harness.shared.exceptions.provider_exceptions import ProviderUnavailableError
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    SandboxMode,
)
from comx_harness.shared.harness_enums.lifecycle_enums import (
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.storage.harness_storage import open_storage
from comx_harness.storage.time_identity import allocate_run_id


def request_for(
    workspace: Path,
    *,
    provider: ProviderId = ProviderId.CODEX,
    objective: str = "Complete the objective.",
    idempotency_key: str | None = None,
    expected_artifacts: tuple[str, ...] = (),
    approval_policy: ApprovalPolicy = ApprovalPolicy.ON_REQUEST,
    search: bool = False,
) -> ExecutionRequest:
    return ExecutionRequest(
        controller_id="test-controller",
        provider=provider,
        objective=objective,
        workspace=str(workspace),
        idempotency_key=idempotency_key,
        expected_artifacts=expected_artifacts,
        options=RunOptions(
            sandbox=SandboxMode.READ_ONLY,
            approval_policy=approval_policy,
            search=search,
        ),
    )


def test_capabilities_and_plan_use_native_provider_contract(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()

    report = service.capabilities()
    plan = service.plan(request_for(tmp_path))

    assert {provider.provider for provider in report.providers} == {"codex", "omx"}
    assert all(provider.available for provider in report.providers)
    assert plan.provider == "codex"
    assert plan.argv[0].endswith("codex")
    assert plan.argv[1:3] == ("exec", "--json")
    assert "-o" in plan.argv
    assert "-a" not in plan.argv
    assert "--search" not in plan.argv
    assert 'approval_policy="on-request"' in plan.argv
    assert plan.supports_cancel is True
    assert plan.supports_resume is True
    assert not (tmp_path / ".comx-agent").exists()


def test_plan_maps_search_and_approval_to_exec_config_overrides(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()

    plan = service.plan(
        request_for(
            tmp_path,
            provider=ProviderId.OMX,
            approval_policy=ApprovalPolicy.NEVER,
            search=True,
        )
    )

    assert plan.argv[0].endswith("omx")
    assert plan.argv[1:3] == ("exec", "--json")
    assert 'approval_policy="never"' in plan.argv
    assert 'web_search="live"' in plan.argv
    assert "-a" not in plan.argv
    assert "--search" not in plan.argv


def test_capabilities_report_missing_providers_without_simulation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "missing-bin"))
    service = HarnessService()

    report = service.capabilities()

    assert all(provider.available is False for provider in report.providers)
    with pytest.raises(ProviderUnavailableError):
        service.plan(request_for(tmp_path))


def test_capabilities_reject_an_installed_but_incompatible_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = tmp_path / "incompatible-bin"
    bin_dir.mkdir()
    script = """#!/bin/sh
if [ "${1:-}" = "--version" ]; then
  echo "incompatible 1.0.0"
  exit 0
fi
printf 'error: unexpected argument from incompatible native parser\n' >&2
exit 2
"""
    for binary_name in ("codex", "omx"):
        binary_path = bin_dir / binary_name
        binary_path.write_text(script)
        binary_path.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    service = HarnessService()

    report = service.capabilities()

    assert all(provider.available for provider in report.providers)
    for provider in report.providers:
        capabilities = {item.operation: item for item in provider.capabilities}
        assert capabilities["run"].supported is False
        assert capabilities["resume"].supported is False
        assert "parser rejected" in capabilities["run"].detail
        assert capabilities["status"].supported is True
        assert capabilities["events"].supported is True
        assert capabilities["artifacts"].supported is True
    with pytest.raises(ProviderUnavailableError, match="incompatible"):
        service.plan(request_for(tmp_path))


def test_direct_run_verifies_result_events_and_status(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()

    record = service.run(request_for(tmp_path))
    state = service.status(tmp_path, record.run_id)
    events = service.events(tmp_path, record.run_id)
    artifacts = service.artifacts(tmp_path, record.run_id)

    assert record.status == RunStatus.SUCCEEDED
    assert record.provider_session_id == "session-123"
    assert state.liveness == ProcessLiveness.FINISHED
    assert any(event.provider_event_type == "thread.started" for event in events.events)
    result = next(item for item in artifacts.artifacts if item.kind == "result")
    assert result.exists is True
    assert result.size_bytes > 0
    assert result.sha256 is not None


def test_terminal_record_matches_final_events_artifact_bytes(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()

    record = service.run(request_for(tmp_path))
    persisted_record = service.status(tmp_path, record.run_id).record
    events_artifact = next(
        item for item in persisted_record.verified_artifacts if item.kind == "events"
    )
    events_path = Path(events_artifact.path)
    events_bytes = events_path.read_bytes()

    assert events_artifact.size_bytes == len(events_bytes)
    assert events_artifact.sha256 == sha256(events_bytes).hexdigest()


def test_status_persists_stale_state_when_the_recorded_process_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HarnessService()
    storage = open_storage(tmp_path)
    run_id = allocate_run_id()
    storage.runs.ensure_run(run_id)
    storage.runs.write_record(
        RunRecord(
            run_id=run_id,
            owner_controller_id="test-controller",
            provider=ProviderId.CODEX,
            objective="Recover stale lifecycle state.",
            status=RunStatus.RUNNING,
            plan_path=str(storage.layout.run_paths(run_id).plan),
            pid=12345,
            started_at="2026-07-28T00:00:00Z",
        )
    )
    monkeypatch.setattr(
        "comx_harness.application.harness_service.process_liveness",
        lambda record: ProcessLiveness.MISSING,
    )

    state = service.status(tmp_path, run_id)
    persisted = storage.runs.read_record(run_id)
    events = service.events(tmp_path, run_id)

    assert state.record.status == RunStatus.STALE
    assert persisted.status == RunStatus.STALE
    assert persisted.finished_at is not None
    assert persisted.failure is not None
    assert persisted.failure.code == "process_missing"
    assert any("marked stale" in event.message for event in events.events)


def test_idempotency_returns_the_existing_run(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    request = request_for(tmp_path, idempotency_key="stable-request")

    first = service.run(request)
    second = service.run(request)

    assert second.run_id == first.run_id


def test_idempotent_plan_preview_matches_the_executed_run(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    request = request_for(tmp_path, idempotency_key="operator-plan-preview")

    preview = service.plan(request)
    record = service.run(request)
    persisted = open_storage(tmp_path).runs.read_plan(record.run_id)

    assert record.run_id == preview.run_id
    assert persisted.run_id == preview.run_id
    assert persisted.argv == preview.argv
    assert persisted.result_path == preview.result_path


def test_concurrent_idempotent_requests_execute_only_one_native_run(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HarnessService()
    request = request_for(tmp_path, idempotency_key="concurrent-request")
    barrier = threading.Barrier(2)
    monkeypatch.setenv("FAKE_PROVIDER_SLEEP", "0.5")

    def execute() -> RunRecord:
        barrier.wait(timeout=5)
        return service.run(request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(execute) for _ in range(2))
        records = tuple(future.result(timeout=10) for future in futures)

    run_ids = {record.run_id for record in records}
    run_directories = tuple(
        path
        for path in (tmp_path / ".comx-agent" / "v2" / "runs").iterdir()
        if path.is_dir()
    )
    final_record = service.status(tmp_path, records[0].run_id).record
    events = service.events(tmp_path, records[0].run_id)

    assert len(run_ids) == 1
    assert len(run_directories) == 1
    assert final_record.status == RunStatus.SUCCEEDED
    assert (
        sum("native process started" in event.message for event in events.events) == 1
    )


def test_concurrent_conflicting_idempotency_requests_fail_closed(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HarnessService()
    barrier = threading.Barrier(2)
    monkeypatch.setenv("FAKE_PROVIDER_SLEEP", "0.5")
    requests = (
        request_for(
            tmp_path,
            objective="Implement the approved change.",
            idempotency_key="conflicting-request",
        ),
        request_for(
            tmp_path,
            objective="Perform a different operation.",
            idempotency_key="conflicting-request",
        ),
    )

    def execute(request: ExecutionRequest) -> RunRecord | IdempotencyConflictError:
        barrier.wait(timeout=5)
        try:
            return service.run(request)
        except IdempotencyConflictError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(execute, request) for request in requests)
        outcomes = tuple(future.result(timeout=10) for future in futures)

    successful_runs = tuple(
        outcome for outcome in outcomes if isinstance(outcome, RunRecord)
    )
    conflicts = tuple(
        outcome for outcome in outcomes if isinstance(outcome, IdempotencyConflictError)
    )
    run_directories = tuple(
        path
        for path in (tmp_path / ".comx-agent" / "v2" / "runs").iterdir()
        if path.is_dir()
    )

    assert len(successful_runs) == 1
    assert len(conflicts) == 1
    assert len(run_directories) == 1


def test_idempotency_rejects_a_different_request_for_the_same_key(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    service.run(
        request_for(
            tmp_path,
            objective="Implement the requested change.",
            idempotency_key="stable-request",
        )
    )

    with pytest.raises(IdempotencyConflictError):
        service.run(
            request_for(
                tmp_path,
                objective="Delete unrelated files.",
                idempotency_key="stable-request",
            )
        )


def test_missing_declared_artifact_blocks_semantic_success(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()

    record = service.run(
        request_for(tmp_path, expected_artifacts=("missing-evidence.md",))
    )

    assert record.status == RunStatus.BLOCKED
    assert record.exit_code == 0
    assert record.failure is not None
    assert record.failure.code == "evidence_missing"


def test_codex_to_omx_handoff_preserves_provenance(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.CODEX))

    result = service.handoff(
        tmp_path,
        HandoffRequest(
            controller_id="hermes-reviewer",
            origin_run_id=source.run_id,
            target_provider=ProviderId.OMX,
            objective="Review the source result.",
        ),
    )

    assert result.handoff.origin_run_id == source.run_id
    assert result.handoff.source_provider == "codex"
    assert result.handoff.target_provider == "omx"
    assert result.handoff.source_artifact.sha256 is not None
    assert result.target_run.provider == "omx"
    assert result.target_run.status == RunStatus.SUCCEEDED


def test_omx_to_codex_handoff_preserves_provenance(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.OMX))

    result = service.handoff(
        tmp_path,
        HandoffRequest(
            controller_id="hermes-builder",
            origin_run_id=source.run_id,
            target_provider=ProviderId.CODEX,
            objective="Implement from the reviewed source result.",
        ),
    )

    assert result.handoff.origin_run_id == source.run_id
    assert result.handoff.source_provider == "omx"
    assert result.handoff.target_provider == "codex"
    assert result.handoff.source_artifact.sha256 is not None
    assert result.target_run.provider == "codex"
    assert result.target_run.status == RunStatus.SUCCEEDED


def test_idempotent_handoff_returns_the_existing_provenance_and_target_run(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.CODEX))
    request = HandoffRequest(
        controller_id="hermes-reviewer",
        origin_run_id=source.run_id,
        target_provider=ProviderId.OMX,
        objective="Review the source result once.",
        idempotency_key="stable-handoff",
    )

    first = service.handoff(tmp_path, request)
    second = service.handoff(tmp_path, request)

    assert second.handoff.handoff_id == first.handoff.handoff_id
    assert second.target_run.run_id == first.target_run.run_id
    assert (
        len(tuple((tmp_path / ".comx-agent" / "v2" / "handoffs").glob("*.json"))) == 1
    )


def test_concurrent_idempotent_handoffs_execute_only_one_target_run(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.CODEX))
    request = HandoffRequest(
        origin_run_id=source.run_id,
        target_provider=ProviderId.OMX,
        objective="Review exactly once.",
        idempotency_key="concurrent-handoff",
    )
    barrier = threading.Barrier(2)
    monkeypatch.setenv("FAKE_PROVIDER_SLEEP", "0.5")

    def execute() -> HandoffResult:
        barrier.wait(timeout=5)
        return service.handoff(tmp_path, request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(execute) for _ in range(2))
        results = tuple(future.result(timeout=10) for future in futures)

    handoff_ids = {result.handoff.handoff_id for result in results}
    target_run_ids = {result.target_run.run_id for result in results}
    run_directories = tuple(
        path
        for path in (tmp_path / ".comx-agent" / "v2" / "runs").iterdir()
        if path.is_dir()
    )

    assert len(handoff_ids) == 1
    assert len(target_run_ids) == 1
    assert len(run_directories) == 2


def test_handoff_idempotency_rejects_a_different_request_for_the_same_key(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.CODEX))
    service.handoff(
        tmp_path,
        HandoffRequest(
            origin_run_id=source.run_id,
            target_provider=ProviderId.OMX,
            objective="Review the source result.",
            idempotency_key="conflicting-handoff",
        ),
    )

    with pytest.raises(IdempotencyConflictError):
        service.handoff(
            tmp_path,
            HandoffRequest(
                origin_run_id=source.run_id,
                target_provider=ProviderId.OMX,
                objective="Perform a different receiving operation.",
                idempotency_key="conflicting-handoff",
            ),
        )


def test_same_provider_handoff_is_delegated_to_native_behavior(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.CODEX))

    with pytest.raises(UnsupportedOperationError):
        service.handoff(
            tmp_path,
            HandoffRequest(
                origin_run_id=source.run_id,
                target_provider=ProviderId.CODEX,
                objective="Continue in the same provider.",
            ),
        )


def test_resume_uses_observed_native_session_id(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(
        request_for(
            tmp_path,
            provider=ProviderId.OMX,
            approval_policy=ApprovalPolicy.NEVER,
            search=True,
        )
    )

    resumed = service.resume(tmp_path, source.run_id, "Continue with verification.")
    resumed_plan = open_storage(tmp_path).runs.read_plan(resumed.run_id)

    assert resumed.parent_run_id == source.run_id
    assert resumed.provider == "omx"
    assert resumed.status == RunStatus.SUCCEEDED
    assert 'approval_policy="never"' in resumed_plan.argv
    assert 'web_search="live"' in resumed_plan.argv
    assert "-a" not in resumed_plan.argv
    assert "--search" not in resumed_plan.argv


def test_idempotent_resume_returns_the_existing_continuation(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.OMX))

    first = service.resume(
        tmp_path,
        source.run_id,
        "Continue once.",
        idempotency_key="stable-resume",
    )
    second = service.resume(
        tmp_path,
        source.run_id,
        "Continue once.",
        idempotency_key="stable-resume",
    )

    assert second.run_id == first.run_id
    events = service.events(tmp_path, first.run_id)
    assert (
        sum("native process started" in event.message for event in events.events) == 1
    )


def test_concurrent_idempotent_resumes_execute_only_one_native_run(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.OMX))
    barrier = threading.Barrier(2)
    monkeypatch.setenv("FAKE_PROVIDER_SLEEP", "0.5")

    def execute() -> RunRecord:
        barrier.wait(timeout=5)
        return service.resume(
            tmp_path,
            source.run_id,
            "Continue once.",
            idempotency_key="concurrent-resume",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(executor.submit(execute) for _ in range(2))
        records = tuple(future.result(timeout=10) for future in futures)

    run_directories = tuple(
        path
        for path in (tmp_path / ".comx-agent" / "v2" / "runs").iterdir()
        if path.is_dir()
    )
    final_record = service.status(tmp_path, records[0].run_id).record

    assert len({record.run_id for record in records}) == 1
    assert len(run_directories) == 2
    assert final_record.status == RunStatus.SUCCEEDED


def test_resume_idempotency_rejects_a_different_request_for_the_same_key(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    source = service.run(request_for(tmp_path, provider=ProviderId.OMX))
    service.resume(
        tmp_path,
        source.run_id,
        "Continue with verification.",
        idempotency_key="conflicting-resume",
    )

    with pytest.raises(IdempotencyConflictError):
        service.resume(
            tmp_path,
            source.run_id,
            "Continue with a different objective.",
            idempotency_key="conflicting-resume",
        )


def test_native_output_logs_are_observable_before_process_completion(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_path = tmp_path / "release-provider"
    provider_path = fake_provider_path / "codex"
    provider_path.write_text(
        """#!/bin/sh
if [ "${1:-}" = "--version" ]; then
  echo "codex 1.0.0"
  exit 0
fi
for arg in "$@"; do
  if [ "$arg" = "--help" ]; then
    echo "codex fake help"
    exit 0
  fi
done
output=""
for arg in "$@"; do
  if [ "${previous:-}" = "-o" ]; then
    output="$arg"
  fi
  previous="$arg"
done
printf 'stdout-before-release\\n'
printf 'stderr-before-release\\n' >&2
while [ ! -f "$FAKE_PROVIDER_RELEASE" ]; do
  sleep 0.05
done
(python3 -c 'import os; os.write(1, b"O" * 100000)' ; printf '\\n') &
(python3 -c 'import os; os.write(2, b"E" * 100000)' ; printf '\\n' >&2) &
wait
printf '{"type":"thread.started","thread_id":"stream-session"}\\n'
printf '{"type":"turn.completed"}\\n'
mkdir -p "$(dirname "$output")"
printf '# verified result\\n' > "$output"
""",
        encoding="utf-8",
    )
    provider_path.chmod(0o755)
    monkeypatch.setenv("FAKE_PROVIDER_RELEASE", str(release_path))
    service = HarnessService()
    result: list[RunRecord] = []

    worker = threading.Thread(
        target=lambda: result.append(service.run(request_for(tmp_path)))
    )
    worker.start()

    stdout_path: Path | None = None
    stderr_path: Path | None = None
    running_run_id: str | None = None
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        run_directories = list((tmp_path / ".comx-agent" / "v2" / "runs").glob("*"))
        if run_directories:
            candidate = run_directories[0]
            candidate_stdout = candidate / "stdout.log"
            candidate_stderr = candidate / "stderr.log"
            if (
                candidate_stdout.exists()
                and candidate_stderr.exists()
                and candidate_stdout.read_text(encoding="utf-8")
                and candidate_stderr.read_text(encoding="utf-8")
            ):
                stdout_path = candidate_stdout
                stderr_path = candidate_stderr
                running_run_id = candidate.name
                break
        time.sleep(0.05)

    worker_alive_before_release = worker.is_alive()
    running_status = (
        service.status(tmp_path, running_run_id).record.status
        if running_run_id is not None
        else None
    )
    release_path.touch()
    worker.join(timeout=5)

    assert stdout_path is not None
    assert stderr_path is not None
    assert worker_alive_before_release
    assert running_status == RunStatus.RUNNING
    assert worker.is_alive() is False
    assert result[0].status == RunStatus.SUCCEEDED
    assert result[0].provider_session_id == "stream-session"
    stdout_text = stdout_path.read_text(encoding="utf-8")
    stderr_text = stderr_path.read_text(encoding="utf-8")
    assert stdout_text.startswith("stdout-before-release\n")
    assert stdout_text.count("O") == 100_000
    assert stdout_text.endswith(
        '{"type":"thread.started","thread_id":"stream-session"}\n'
        '{"type":"turn.completed"}\n'
    )
    assert stderr_text.startswith("stderr-before-release\n")
    assert stderr_text.count("E") == 100_000


def test_timeout_stops_the_native_process_group(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HarnessService()
    monkeypatch.setenv("FAKE_PROVIDER_SLEEP", "10")
    request = request_for(tmp_path).model_copy(update={"timeout_seconds": 1})
    started_at = time.monotonic()

    record = service.run(request)

    elapsed = time.monotonic() - started_at
    assert record.status == RunStatus.FAILED
    assert record.failure is not None
    assert record.failure.code == "timeout"
    assert elapsed < 5


def test_cancel_stops_a_recorded_running_process(
    tmp_path: Path,
    fake_provider_path: Path,
    monkeypatch,
) -> None:
    service = HarnessService()
    monkeypatch.setenv("FAKE_PROVIDER_SLEEP", "10")
    result: list = []

    def execute() -> None:
        result.append(service.run(request_for(tmp_path)))

    worker = threading.Thread(target=execute)
    worker.start()
    running_run_id: str | None = None
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        records = list((tmp_path / ".comx-agent" / "v2" / "runs").glob("*/run.json"))
        if records:
            candidate = records[0].parent.name
            state = service.status(tmp_path, candidate)
            if state.record.status == RunStatus.RUNNING:
                running_run_id = candidate
                break
        time.sleep(0.05)

    assert running_run_id is not None
    cancelled = service.cancel(tmp_path, running_run_id)
    worker.join(timeout=5)

    assert cancelled.status == RunStatus.CANCELLED
    assert worker.is_alive() is False
    assert result[0].status == RunStatus.CANCELLED
