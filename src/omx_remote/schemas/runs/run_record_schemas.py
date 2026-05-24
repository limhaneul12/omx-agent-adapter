from enum import StrEnum

from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class RunRecordStatus(StrEnum):
    """Supported run record lifecycle states."""

    PLANNED = "planned"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RunNativeCommand(StrictSchemaModel):
    """Represents one native command captured from a plan."""

    index: int
    argv: tuple[NonEmptyString, ...]


class RunArtifact(StrictSchemaModel):
    """Represents one artifact path written for a run."""

    kind: NonEmptyString
    path: NonEmptyString


class RunVerification(StrictSchemaModel):
    """Represents run verification status."""

    status: NonEmptyString
    evidence: NonEmptyString | None = None


class RunRecord(StrictSchemaModel):
    """Represents a durable composed-command run record."""

    run_id: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    source: NonEmptyString
    cwd: NonEmptyString
    started_at: NonEmptyString
    finished_at: NonEmptyString
    status: RunRecordStatus
    dry_run: bool
    native_commands: tuple[RunNativeCommand, ...]
    artifacts: tuple[RunArtifact, ...]
    verification: RunVerification
    plan_path: NonEmptyString
    stdout_log_path: NonEmptyString
    stderr_log_path: NonEmptyString
    handoff_path: NonEmptyString


class RunListResult(StrictSchemaModel):
    """Represents run list output."""

    records: tuple[RunRecord, ...]


class RunReplayPlan(StrictSchemaModel):
    """Represents a dry-run replay plan loaded from a recorded run."""

    run_id: NonEmptyString
    plan: CommandExecutionPlan


class RunCommandRecordResult(StrictSchemaModel):
    """Represents `agent-remote run --record-run` output."""

    plan: CommandExecutionPlan
    run_record: RunRecord
