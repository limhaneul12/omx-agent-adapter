from pathlib import Path

from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.commands.rendering.command_output_redaction import (
    redact_text,
)
from omx_remote.runtime.runs.run_artifact_store import allocate_unique_run_dir
from omx_remote.runtime.runs.run_native_commands import collect_run_native_commands
from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.schemas.run_record_schemas import (
    RunArtifact,
    RunRecord,
    RunRecordStatus,
    RunVerification,
)
from omx_remote.shared.utils.runtime_identity import utc_compact_timestamp, utcnow_text


def render_run_handoff(record: RunRecord, plan: CommandExecutionPlan) -> str:
    """Render a concise run handoff artifact.

    Args:
        record [RunRecord]: Run record to summarize.
        plan [CommandExecutionPlan]: Recorded execution plan.

    Returns:
        str: Markdown handoff text.
    """
    lines: list[str] = [
        f"# Run {record.run_id}",
        "",
        f"- command: {record.qualified_id}",
        f"- status: {record.status}",
        f"- dry_run: {record.dry_run}",
        f"- plan: {record.plan_path}",
        "",
        "## Planned native commands",
    ]
    lines.extend(
        f"{command.index}. `{' '.join(command.argv)}`"
        for command in record.native_commands
    )
    if plan.blocked_reasons:
        lines.append("")
        lines.append("## Blockers")
        lines.extend(f"- {redact_text(blocker)}" for blocker in plan.blocked_reasons)

    handoff_text: str = "\n".join(lines)
    return handoff_text


def write_dry_run_record(
    plan: CommandExecutionPlan,
    cwd: str | Path,
    timestamp: str | None = None,
) -> RunRecord:
    """Write a dry-run record and artifacts.

    Args:
        plan [CommandExecutionPlan]: Dry-run execution plan to record.
        cwd [str | Path]: Repository root.
        timestamp [str | None]: Optional deterministic timestamp for tests.

    Returns:
        RunRecord: Persisted run record.
    """
    timestamp_text: str = utc_compact_timestamp() if timestamp is None else timestamp
    run_id, run_dir = allocate_unique_run_dir(cwd, timestamp_text, plan.command_id)
    started_at: str = utcnow_text()
    finished_at: str = started_at
    plan_path: Path = run_dir / "plan.json"
    run_path: Path = run_dir / "run.json"
    stdout_path: Path = run_dir / "stdout.log"
    stderr_path: Path = run_dir / "stderr.log"
    handoff_path: Path = run_dir / "handoff.md"
    final_message_path: Path = run_dir / "final-message.md"

    artifacts: tuple[RunArtifact, ...] = (
        RunArtifact(kind="run", path=str(run_path)),
        RunArtifact(kind="plan", path=str(plan_path)),
        RunArtifact(kind="stdout", path=str(stdout_path)),
        RunArtifact(kind="stderr", path=str(stderr_path)),
        RunArtifact(kind="handoff", path=str(handoff_path)),
        RunArtifact(kind="final_message", path=str(final_message_path)),
    )
    record = RunRecord(
        run_id=run_id,
        command_id=plan.command_id,
        qualified_id=plan.qualified_id,
        source=plan.source,
        cwd=str(Path(cwd).resolve()),
        started_at=started_at,
        finished_at=finished_at,
        status=RunRecordStatus.PLANNED,
        dry_run=True,
        native_commands=collect_run_native_commands(plan),
        artifacts=artifacts,
        verification=RunVerification(status="not_run", evidence="dry-run record"),
        plan_path=str(plan_path),
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        handoff_path=str(handoff_path),
    )
    handoff_text: str = render_run_handoff(record, plan)

    write_redacted_json_artifact(plan_path, plan)
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    final_message_path.write_text("", encoding="utf-8")
    handoff_path.write_text(handoff_text, encoding="utf-8")
    write_redacted_json_artifact(run_path, record)
    return record
