from dataclasses import dataclass
from pathlib import Path

from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.commands.rendering.command_output_redaction import redact_text
from omx_remote.runtime.runs.run_artifact_store import allocate_unique_run_dir
from omx_remote.runtime.runs.run_native_commands import collect_run_native_commands
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandActualRunResult,
    CommandActualRunStatus,
    CommandArtifactCheck,
    CommandArtifactChecksPayload,
    CommandAutonomyDecision,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.schemas.run_record_schemas import (
    RunArtifact,
    RunRecord,
    RunRecordStatus,
    RunVerification,
)
from omx_remote.shared.utils.runtime_identity import utc_compact_timestamp


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
    timestamp_text: str = utc_compact_timestamp() if timestamp is None else timestamp
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
    write_redacted_json_artifact(paths.plan_path, plan)
    paths.recovery_path.write_text("# Recovery evidence\n", encoding="utf-8")
    paths.handoff_path.write_text("", encoding="utf-8")
    paths.stdout_log_path.write_text("", encoding="utf-8")
    paths.stderr_log_path.write_text("", encoding="utf-8")
    return paths


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


def _run_record_artifacts(paths: ActualRunPaths) -> tuple[RunArtifact, ...]:
    """Build artifact references shared by planned and final run records.

    Args:
        paths [ActualRunPaths]: Actual run path set.

    Returns:
        tuple[RunArtifact, ...]: Durable run artifact references.
    """
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
    return artifacts


def build_actual_run_record(
    plan: CommandExecutionPlan,
    paths: ActualRunPaths,
    cwd: str | Path,
    status: CommandActualRunStatus,
    started_at: str,
    finished_at: str,
) -> RunRecord:
    """Build a durable run record for actual execution.

    Args:
        plan: See function signature.
        paths: See function signature.
        cwd: See function signature.
        status: See function signature.
        started_at: See function signature.
        finished_at: See function signature.

    Returns:
        See function return annotation."""
    artifacts: tuple[RunArtifact, ...] = _run_record_artifacts(paths)
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
        native_commands=collect_run_native_commands(plan),
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
    artifacts: tuple[RunArtifact, ...] = _run_record_artifacts(paths)
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
        native_commands=collect_run_native_commands(plan),
        artifacts=artifacts,
        verification=RunVerification(status="running", evidence=str(paths.plan_path)),
        plan_path=str(paths.plan_path),
        stdout_log_path=str(paths.stdout_log_path),
        stderr_log_path=str(paths.stderr_log_path),
        handoff_path=str(paths.handoff_path),
    )
    write_redacted_json_artifact(paths.run_record_path, record)
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
    """Persist final actual result and durable run record artifacts.

    Args:
        plan: See function signature.
        paths: See function signature.
        cwd: See function signature.
        result: See function signature.
        autonomy_decision: See function signature.

    Returns:
        See function return annotation."""
    write_redacted_json_artifact(paths.autonomy_decision_path, autonomy_decision)
    write_redacted_json_artifact(paths.result_path, result)
    write_redacted_json_artifact(
        paths.artifacts_path,
        CommandArtifactChecksPayload(artifacts=result.artifact_checks),
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
    write_redacted_json_artifact(paths.run_record_path, record)
    return record
