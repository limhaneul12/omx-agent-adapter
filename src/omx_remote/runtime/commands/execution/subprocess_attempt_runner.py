from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.commands.rendering.command_output_redaction import (
    redact_argv,
    redact_text,
)
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandFailureClassification,
    CommandStepAttempt,
)
from omx_remote.shared.process_environment_settings import ProcessEnvironmentSettings
from omx_remote.shared.utils.runtime_identity import utcnow_text


@dataclass(frozen=True)
class SubprocessAttemptOutcome:
    """Raw subprocess attempt outcome before schema promotion."""

    argv: tuple[str, ...]
    started_at: str
    finished_at: str
    duration_seconds: float
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


def _execution_env(cwd: Path) -> dict[str, str]:
    """Build an execution environment that can import the repo-local package.

    Args:
        cwd: See function signature.

    Returns:
        See function return annotation."""
    env: dict[str, str] = dict(ProcessEnvironmentSettings().environment_values)
    python_paths: list[str] = [str(cwd / "src"), str(cwd / "src" / "omx_remote")]
    existing_pythonpath: str | None = env.get("PYTHONPATH")
    if existing_pythonpath:
        python_paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    return env


def append_global_logs(paths: ActualRunPaths, stdout: str, stderr: str) -> None:
    """Append redacted attempt output to run-level stdout/stderr logs.

    Args:
        paths: See function signature.
        stdout: See function signature.
        stderr: See function signature."""
    with paths.stdout_log_path.open("a", encoding="utf-8") as stdout_file:
        stdout_file.write(redact_text(stdout))
    with paths.stderr_log_path.open("a", encoding="utf-8") as stderr_file:
        stderr_file.write(redact_text(stderr))


def run_subprocess(
    argv: tuple[str, ...],
    cwd: Path,
    timeout_seconds: float,
) -> SubprocessAttemptOutcome:
    """Run one subprocess attempt and capture stdout/stderr.

    Args:
        argv: See function signature.
        cwd: See function signature.
        timeout_seconds: See function signature.

    Returns:
        See function return annotation."""
    started_at: str = utcnow_text()
    started_time: float = time.monotonic()
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=_execution_env(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            finished_at: str = utcnow_text()
            duration: float = time.monotonic() - started_time
            outcome = SubprocessAttemptOutcome(
                argv=argv,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
            )
            return outcome
        except subprocess.TimeoutExpired:
            if hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            stdout, stderr = process.communicate()
            finished_at = utcnow_text()
            duration = time.monotonic() - started_time
            outcome = SubprocessAttemptOutcome(
                argv=argv,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=duration,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )
            return outcome
    except OSError as error:
        finished_at = utcnow_text()
        duration = time.monotonic() - started_time
        outcome = SubprocessAttemptOutcome(
            argv=argv,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            exit_code=127,
            stdout="",
            stderr=str(error),
            timed_out=False,
        )
        return outcome


def _attempt_paths(
    paths: ActualRunPaths, step_index: int, attempt: int
) -> tuple[Path, Path, Path, Path]:
    """Create and return step attempt artifact paths.

    Args:
        paths: See function signature.
        step_index: See function signature.
        attempt: See function signature.

    Returns:
        See function return annotation."""
    attempt_dir = (
        paths.run_dir / "steps" / f"{step_index:03d}" / "attempts" / f"{attempt:03d}"
    )
    attempt_dir.mkdir(parents=True, exist_ok=True)
    argv_path: Path = attempt_dir / "argv.json"
    stdout_path: Path = attempt_dir / "stdout.txt"
    stderr_path: Path = attempt_dir / "stderr.txt"
    result_path: Path = attempt_dir / "result.json"
    return argv_path, stdout_path, stderr_path, result_path


def write_attempt(
    paths: ActualRunPaths,
    step_index: int,
    attempt: int,
    outcome: SubprocessAttemptOutcome,
    classification: CommandFailureClassification | None,
) -> CommandStepAttempt:
    """Persist attempt artifacts and promote them to a typed attempt result.

    Args:
        paths: See function signature.
        step_index: See function signature.
        attempt: See function signature.
        outcome: See function signature.
        classification: See function signature.

    Returns:
        See function return annotation."""
    argv_path, stdout_path, stderr_path, result_path = _attempt_paths(
        paths, step_index, attempt
    )
    redacted_argv = redact_argv(outcome.argv)
    redacted_stdout = redact_text(outcome.stdout)
    redacted_stderr = redact_text(outcome.stderr)
    write_redacted_json_artifact(argv_path, {"argv": list(redacted_argv)})
    stdout_path.write_text(redacted_stdout, encoding="utf-8")
    stderr_path.write_text(redacted_stderr, encoding="utf-8")
    attempt_result = CommandStepAttempt(
        step_index=step_index,
        attempt=attempt,
        argv=redacted_argv,
        started_at=outcome.started_at,
        finished_at=outcome.finished_at,
        duration_seconds=outcome.duration_seconds,
        exit_code=outcome.exit_code,
        timed_out=outcome.timed_out,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        result_path=str(result_path),
        classification=classification,
    )
    write_redacted_json_artifact(result_path, attempt_result)
    append_global_logs(paths, outcome.stdout, outcome.stderr)
    return attempt_result
