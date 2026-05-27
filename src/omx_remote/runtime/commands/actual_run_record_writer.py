from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import orjson

from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.runtime.commands.command_output_redaction import (
    redact_argv,
    redact_json_artifact,
    redact_text,
)
from omx_remote.runtime.runs.run_artifact_store import allocate_unique_run_dir
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandActualRunResult,
    CommandActualRunStatus,
    CommandArtifactCheck,
    CommandAutonomyDecision,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.schemas.runs.run_record_schemas import (
    RunArtifact,
    RunNativeCommand,
    RunRecord,
    RunRecordStatus,
    RunVerification,
)


@dataclass(frozen=True)
class ActualRunPaths:
    """Filesystem paths for one actual command run."""

    run_id: str
    run_dir: Path
    plan_path: Path
    run_record_path: Path
    autonomy_decision_path: Path
    result_path: Path
    artifacts_path: Path
    recovery_path: Path
    handoff_path: Path
    stdout_log_path: Path
    stderr_log_path: Path


def now_timestamp() -> str:
    """Return a compact UTC timestamp for actual run ids.

    Returns:
        See function return annotation."""
    timestamp: str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return timestamp


def now_iso() -> str:
    """Return an ISO-8601 UTC timestamp.

    Returns:
        See function return annotation."""
    timestamp: str = datetime.now(UTC).isoformat()
    return timestamp


def write_json_artifact(path: Path, value: object) -> None:
    """Write one JSON artifact using the repository transport library.

    Args:
        path: See function signature.
        value: See function signature."""
    path.parent.mkdir(parents=True, exist_ok=True)
    redacted_value: JsonValue = redact_json_artifact(cast(JsonValue, value))
    path.write_bytes(orjson.dumps(redacted_value, option=orjson.OPT_INDENT_2))


def initialize_actual_run(
    plan: CommandExecutionPlan,
    cwd: str | Path,
    timestamp: str | None = None,
) -> ActualRunPaths:
    """Create run directories and write initial immutable plan artifacts.

    Args:
        plan: See function signature.
        cwd: See function signature.
        timestamp: See function signature.

    Returns:
        See function return annotation."""
    timestamp_text: str = now_timestamp() if timestamp is None else timestamp
    run_id, run_dir = allocate_unique_run_dir(cwd, timestamp_text, plan.command_id)
    paths = ActualRunPaths(
        run_id=run_id,
        run_dir=run_dir,
        plan_path=run_dir / "plan.json",
        run_record_path=run_dir / "run.json",
        autonomy_decision_path=run_dir / "autonomy-decision.json",
        result_path=run_dir / "result.json",
        artifacts_path=run_dir / "artifacts.json",
        recovery_path=run_dir / "recovery.md",
        handoff_path=run_dir / "handoff.md",
        stdout_log_path=run_dir / "stdout.log",
        stderr_log_path=run_dir / "stderr.log",
    )
    write_json_artifact(paths.plan_path, plan.model_dump(mode="json"))
    paths.recovery_path.write_text("# Recovery evidence\n", encoding="utf-8")
    paths.handoff_path.write_text("", encoding="utf-8")
    paths.stdout_log_path.write_text("", encoding="utf-8")
    paths.stderr_log_path.write_text("", encoding="utf-8")
    return paths


def native_commands(plan: CommandExecutionPlan) -> tuple[RunNativeCommand, ...]:
    """Collect native command previews from a plan.

    Args:
        plan: See function signature.

    Returns:
        See function return annotation."""
    commands: tuple[RunNativeCommand, ...] = tuple(
        RunNativeCommand(index=step.index, argv=redact_argv(step.native_argv))
        for step in plan.steps
        if step.native_argv
    )
    return commands


def run_record_status(status: CommandActualRunStatus) -> RunRecordStatus:
    """Map actual execution status to the durable run record status.

    Args:
        status: See function signature.

    Returns:
        See function return annotation."""
    if status == CommandActualRunStatus.SUCCEEDED:
        mapped_status = RunRecordStatus.SUCCEEDED
        return mapped_status
    if status == CommandActualRunStatus.REQUIRES_AGENT_ACTION:
        mapped_status = RunRecordStatus.REQUIRES_AGENT_ACTION
        return mapped_status
    if status == CommandActualRunStatus.BLOCKED:
        mapped_status = RunRecordStatus.BLOCKED
        return mapped_status
    mapped_status = RunRecordStatus.FAILED
    return mapped_status


def build_actual_run_record(
    plan: CommandExecutionPlan,
    paths: ActualRunPaths,
    cwd: str | Path,
    status: CommandActualRunStatus,
    started_at: str,
    finished_at: str,
) -> RunRecord:
    """Build a backwards-compatible run record for actual execution.

    Args:
        plan: See function signature.
        paths: See function signature.
        cwd: See function signature.
        status: See function signature.
        started_at: See function signature.
        finished_at: See function signature.

    Returns:
        See function return annotation."""
    artifacts: tuple[RunArtifact, ...] = (
        RunArtifact(kind="run", path=str(paths.run_record_path)),
        RunArtifact(kind="plan", path=str(paths.plan_path)),
        RunArtifact(kind="autonomy_decision", path=str(paths.autonomy_decision_path)),
        RunArtifact(kind="result", path=str(paths.result_path)),
        RunArtifact(kind="artifacts", path=str(paths.artifacts_path)),
        RunArtifact(kind="recovery", path=str(paths.recovery_path)),
        RunArtifact(kind="handoff", path=str(paths.handoff_path)),
        RunArtifact(kind="stdout", path=str(paths.stdout_log_path)),
        RunArtifact(kind="stderr", path=str(paths.stderr_log_path)),
    )
    record = RunRecord(
        run_id=paths.run_id,
        command_id=plan.command_id,
        qualified_id=plan.qualified_id,
        source=plan.source,
        cwd=str(Path(cwd).resolve()),
        started_at=started_at,
        finished_at=finished_at,
        status=run_record_status(status),
        dry_run=False,
        native_commands=native_commands(plan),
        artifacts=artifacts,
        verification=RunVerification(status=status, evidence=str(paths.result_path)),
        plan_path=str(paths.plan_path),
        stdout_log_path=str(paths.stdout_log_path),
        stderr_log_path=str(paths.stderr_log_path),
        handoff_path=str(paths.handoff_path),
    )
    return record


def persist_initial_run_record(
    plan: CommandExecutionPlan,
    paths: ActualRunPaths,
    cwd: str | Path,
    started_at: str,
) -> RunRecord:
    """Persist a planned actual run record before step execution starts.

    Args:
        plan: See function signature.
        paths: See function signature.
        cwd: See function signature.
        started_at: See function signature.

    Returns:
        See function return annotation."""
    artifacts: tuple[RunArtifact, ...] = (
        RunArtifact(kind="run", path=str(paths.run_record_path)),
        RunArtifact(kind="plan", path=str(paths.plan_path)),
        RunArtifact(kind="autonomy_decision", path=str(paths.autonomy_decision_path)),
        RunArtifact(kind="result", path=str(paths.result_path)),
        RunArtifact(kind="artifacts", path=str(paths.artifacts_path)),
        RunArtifact(kind="recovery", path=str(paths.recovery_path)),
        RunArtifact(kind="handoff", path=str(paths.handoff_path)),
        RunArtifact(kind="stdout", path=str(paths.stdout_log_path)),
        RunArtifact(kind="stderr", path=str(paths.stderr_log_path)),
    )
    record = RunRecord(
        run_id=paths.run_id,
        command_id=plan.command_id,
        qualified_id=plan.qualified_id,
        source=plan.source,
        cwd=str(Path(cwd).resolve()),
        started_at=started_at,
        finished_at=started_at,
        status=RunRecordStatus.PLANNED,
        dry_run=False,
        native_commands=native_commands(plan),
        artifacts=artifacts,
        verification=RunVerification(status="running", evidence=str(paths.plan_path)),
        plan_path=str(paths.plan_path),
        stdout_log_path=str(paths.stdout_log_path),
        stderr_log_path=str(paths.stderr_log_path),
        handoff_path=str(paths.handoff_path),
    )
    write_json_artifact(paths.run_record_path, record.model_dump(mode="json"))
    return record


def render_actual_handoff(
    result: CommandActualRunResult,
    artifact_checks: tuple[CommandArtifactCheck, ...],
) -> str:
    """Render a concise actual execution handoff artifact.

    Args:
        result: See function signature.
        artifact_checks: See function signature.

    Returns:
        See function return annotation."""
    lines: list[str] = [
        f"# Actual run {result.run_id}",
        "",
        f"- command: {result.qualified_id}",
        f"- status: {result.status}",
        f"- plan: {result.plan_path}",
        f"- result: {result.result_path}",
        f"- recovery: {result.recovery_path}",
        "",
        "## Steps",
    ]
    lines.extend(
        f"{step.index}. {step.command} — {step.status}" for step in result.steps
    )
    if artifact_checks:
        lines.append("")
        lines.append("## Artifact checks")
        lines.extend(
            f"- [{'x' if check.exists else ' '}] {check.path}"
            for check in artifact_checks
        )
    handoff_text: str = "\n".join(lines)
    return handoff_text


def persist_actual_result(
    plan: CommandExecutionPlan,
    paths: ActualRunPaths,
    cwd: str | Path,
    result: CommandActualRunResult,
    autonomy_decision: CommandAutonomyDecision,
) -> RunRecord:
    """Persist final actual result and compatible run record artifacts.

    Args:
        plan: See function signature.
        paths: See function signature.
        cwd: See function signature.
        result: See function signature.
        autonomy_decision: See function signature.

    Returns:
        See function return annotation."""
    write_json_artifact(
        paths.autonomy_decision_path, autonomy_decision.model_dump(mode="json")
    )
    write_json_artifact(paths.result_path, result.model_dump(mode="json"))
    write_json_artifact(
        paths.artifacts_path,
        {
            "artifacts": [
                check.model_dump(mode="json") for check in result.artifact_checks
            ]
        },
    )
    handoff_text: str = redact_text(
        render_actual_handoff(result, result.artifact_checks)
    )
    paths.handoff_path.write_text(handoff_text, encoding="utf-8")
    record = build_actual_run_record(
        plan,
        paths,
        cwd,
        result.status,
        result.started_at,
        result.finished_at,
    )
    write_json_artifact(paths.run_record_path, record.model_dump(mode="json"))
    return record
