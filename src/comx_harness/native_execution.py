from __future__ import annotations

import os
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import IO

from comx_harness.event_normalization import append_run_event, record_provider_output
from comx_harness.run_evidence import (
    collect_run_artifacts,
    required_artifact_failures,
)
from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.execution_schemas import ExecutionPlan
from comx_harness.schemas.lifecycle_schemas import RunFailure, RunRecord
from comx_harness.shared.harness_enums.lifecycle_enums import (
    EventKind,
    ProcessLiveness,
    RunStatus,
)
from comx_harness.storage.harness_storage import HarnessStorage
from comx_harness.storage.time_identity import utc_timestamp


class NativeRunExecutor:
    """Launch one native provider process and persist terminal evidence."""

    def execute(self, *, plan: ExecutionPlan, storage: HarnessStorage) -> RunRecord:
        storage.runs.ensure_run(plan.run_id)
        started_at = utc_timestamp()
        try:
            process = subprocess.Popen(
                plan.argv,
                cwd=plan.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            failed_record = self._persist_launch_failure(
                plan=plan,
                storage=storage,
                started_at=started_at,
                error=error,
            )
            return failed_record

        running_record = RunRecord(
            run_id=plan.run_id,
            owner_controller_id=plan.request.controller_id,
            provider=plan.provider,
            objective=plan.request.objective,
            status=RunStatus.RUNNING,
            plan_path=str(storage.layout.run_paths(plan.run_id).plan),
            pid=process.pid,
            started_at=started_at,
            parent_run_id=plan.parent_run_id,
        )
        storage.runs.write_record(running_record)
        append_run_event(
            storage,
            run_id=plan.run_id,
            kind=EventKind.LIFECYCLE,
            message=f"native process started pid={process.pid}",
        )

        stdout_pipe = process.stdout
        stderr_pipe = process.stderr
        if stdout_pipe is None or stderr_pipe is None:
            raise RuntimeError("native process pipes were not created")
        with ThreadPoolExecutor(max_workers=2) as output_workers:
            # Drain both pipes concurrently so one full provider pipe cannot block the other.
            stdout_future = output_workers.submit(
                _capture_pipe_to_log,
                pipe=stdout_pipe,
                log_path=Path(plan.stdout_path),
            )
            stderr_future = output_workers.submit(
                _capture_pipe_to_log,
                pipe=stderr_pipe,
                log_path=Path(plan.stderr_path),
            )
            timed_out = _wait_for_process(
                process=process,
                timeout_seconds=plan.request.timeout_seconds,
            )
            # Normalize only after both EOFs so terminal evidence sees complete output.
            stdout_text = stdout_future.result().decode("utf-8", errors="replace")
            stderr_text = stderr_future.result().decode("utf-8", errors="replace")
        provider_session_id = record_provider_output(
            storage,
            plan.run_id,
            stdout_text,
            stderr_text,
        )
        current_record = storage.runs.read_record(plan.run_id)
        outcome_artifacts = collect_run_artifacts(
            storage,
            current_record,
            include_declared=True,
        )
        status, failure = self._terminal_outcome(
            current_record=current_record,
            exit_code=process.returncode,
            timed_out=timed_out,
            missing_required=required_artifact_failures(outcome_artifacts),
            timeout_seconds=plan.request.timeout_seconds,
        )
        append_run_event(
            storage,
            run_id=plan.run_id,
            kind=EventKind.VERIFICATION,
            message=f"terminal status={status}",
        )
        # Recollect after the terminal append so events metadata covers final bytes.
        artifacts = collect_run_artifacts(
            storage,
            current_record,
            include_declared=True,
        )
        terminal_record = running_record.model_copy(
            update={
                "status": status,
                "finished_at": utc_timestamp(),
                "exit_code": process.returncode,
                "provider_session_id": provider_session_id,
                "verified_artifacts": artifacts,
                "failure": failure,
            }
        )
        storage.runs.write_record(terminal_record)
        return terminal_record

    def _terminal_outcome(
        self,
        *,
        current_record: RunRecord,
        exit_code: int | None,
        timed_out: bool,
        missing_required: tuple[VerifiedArtifact, ...],
        timeout_seconds: int,
    ) -> tuple[RunStatus, RunFailure | None]:
        cancelled_by_signal = exit_code in {-signal.SIGTERM, -signal.SIGKILL}
        if current_record.status == RunStatus.CANCELLED:
            failure = current_record.failure or RunFailure(
                code="cancelled",
                message="native process terminated by cancellation signal",
                retryable=True,
            )
            outcome = (RunStatus.CANCELLED, failure)
            return outcome
        if timed_out:
            outcome = (
                RunStatus.FAILED,
                RunFailure(
                    code="timeout",
                    message=f"native process exceeded {timeout_seconds} seconds",
                    retryable=True,
                ),
            )
            return outcome
        if cancelled_by_signal:
            outcome = (
                RunStatus.CANCELLED,
                RunFailure(
                    code="cancelled",
                    message="native process terminated by cancellation signal",
                    retryable=True,
                ),
            )
            return outcome
        if exit_code != 0:
            outcome = (
                RunStatus.FAILED,
                RunFailure(
                    code="provider_exit",
                    message=f"native provider exited with code {exit_code}",
                    retryable=True,
                ),
            )
            return outcome
        if missing_required:
            missing_text = ", ".join(item.path for item in missing_required)
            outcome = (
                RunStatus.BLOCKED,
                RunFailure(
                    code="evidence_missing",
                    message=f"required evidence is missing or empty: {missing_text}",
                    retryable=True,
                ),
            )
            return outcome
        outcome = (RunStatus.SUCCEEDED, None)
        return outcome

    def _persist_launch_failure(
        self,
        *,
        plan: ExecutionPlan,
        storage: HarnessStorage,
        started_at: str,
        error: OSError,
    ) -> RunRecord:
        failed_record = RunRecord(
            run_id=plan.run_id,
            owner_controller_id=plan.request.controller_id,
            provider=plan.provider,
            objective=plan.request.objective,
            status=RunStatus.FAILED,
            plan_path=str(storage.layout.run_paths(plan.run_id).plan),
            started_at=started_at,
            finished_at=utc_timestamp(),
            failure=RunFailure(
                code="launch_failed",
                message=str(error),
                retryable=True,
            ),
            parent_run_id=plan.parent_run_id,
        )
        storage.runs.write_record(failed_record)
        return failed_record


def _capture_pipe_to_log(*, pipe: IO[bytes], log_path: Path) -> bytes:
    """Persist available provider bytes immediately while retaining full output."""
    captured_chunks: list[bytes] = []
    with pipe, log_path.open("wb") as log_file:
        while chunk := os.read(pipe.fileno(), 65_536):
            log_file.write(chunk)
            log_file.flush()
            captured_chunks.append(chunk)
    captured_output = b"".join(captured_chunks)
    return captured_output


def _wait_for_process(
    *,
    process: subprocess.Popen[bytes],
    timeout_seconds: int,
) -> bool:
    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        signal_process_group(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            signal_process_group(process.pid, signal.SIGKILL)
            process.wait()
    return timed_out


def signal_process_group(pid: int, termination_signal: signal.Signals) -> None:
    """Signal one isolated provider process group, falling back to its leader."""
    try:
        os.killpg(pid, termination_signal)
    except ProcessLookupError:
        raise
    except OSError:
        os.kill(pid, termination_signal)


def process_liveness(record: RunRecord) -> ProcessLiveness:
    """Observe local process liveness independently from semantic status."""
    if record.status == RunStatus.PLANNED:
        return ProcessLiveness.NOT_STARTED
    if record.status != RunStatus.RUNNING:
        return ProcessLiveness.FINISHED
    if record.pid is None:
        return ProcessLiveness.MISSING
    try:
        os.kill(record.pid, 0)
    except ProcessLookupError:
        return ProcessLiveness.MISSING
    except PermissionError:
        return ProcessLiveness.RUNNING
    return ProcessLiveness.RUNNING
