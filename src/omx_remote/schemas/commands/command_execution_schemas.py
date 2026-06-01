from pydantic import Field

from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.command_enums import (
    CommandActualRunStatus,
    CommandAutonomyDecisionKind,
    CommandAutonomyMode,
    CommandFailureKind,
    CommandRecoveryAction,
    CommandStepCommand,
    CommandStepExecutionStatus,
)


class CommandAutonomyDecision(StrictSchemaModel):
    """Policy decision for an actual command run."""

    mode: CommandAutonomyMode = CommandAutonomyMode.AGENT
    decision: CommandAutonomyDecisionKind
    reason: NonEmptyString
    required_safeguards: tuple[NonEmptyString, ...] = ()
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CommandArtifactCheck(StrictSchemaModel):
    """Verification result for one expected or produced artifact."""

    path: NonEmptyString
    exists: bool
    size_bytes: int = Field(ge=0)
    sha256: NonEmptyString | None = None
    required: bool = True
    note: NonEmptyString | None = None


class CommandArtifactChecksPayload(StrictSchemaModel):
    """Run-level payload containing expected/produced artifact checks."""

    artifacts: tuple[CommandArtifactCheck, ...]


class CommandFailureClassification(StrictSchemaModel):
    """Normalized classification for a step failure."""

    kind: CommandFailureKind
    reason: NonEmptyString
    retryable: bool = False


class CommandRetryDecision(StrictSchemaModel):
    """Retry or recovery decision after a failed attempt."""

    action: CommandRecoveryAction
    reason: NonEmptyString
    attempt: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    next_delay_seconds: float = Field(ge=0.0, default=0.0)


class CommandStepAttempt(StrictSchemaModel):
    """One subprocess/tool attempt for a command step."""

    step_index: int = Field(ge=1)
    attempt: int = Field(ge=1)
    argv: tuple[NonEmptyString, ...]
    started_at: NonEmptyString
    finished_at: NonEmptyString
    duration_seconds: float = Field(ge=0.0)
    exit_code: int | None = None
    timed_out: bool = False
    stdout_path: NonEmptyString
    stderr_path: NonEmptyString
    result_path: NonEmptyString
    classification: CommandFailureClassification | None = None


class CommandStepExecutionResult(StrictSchemaModel):
    """Actual execution result for one planned command step."""

    index: int = Field(ge=1)
    command: CommandStepCommand
    status: CommandStepExecutionStatus
    attempts: tuple[CommandStepAttempt, ...] = ()
    artifact_checks: tuple[CommandArtifactCheck, ...] = ()
    handoff_path: NonEmptyString | None = None
    failure: CommandFailureClassification | None = None
    retry_decisions: tuple[CommandRetryDecision, ...] = ()


class CommandActualRunResult(StrictSchemaModel):
    """Typed public result for `comx-agent run --execute`."""

    run_id: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    cwd: NonEmptyString
    dry_run: bool = False
    runtime_options: CommandRuntimeOptions | None = None
    status: CommandActualRunStatus
    started_at: NonEmptyString
    finished_at: NonEmptyString
    run_dir: NonEmptyString
    plan_path: NonEmptyString
    autonomy_decision_path: NonEmptyString
    result_path: NonEmptyString
    artifacts_path: NonEmptyString
    recovery_path: NonEmptyString
    autonomy_decision: CommandAutonomyDecision
    steps: tuple[CommandStepExecutionResult, ...]
    artifact_checks: tuple[CommandArtifactCheck, ...] = ()
    blocked_reasons: tuple[NonEmptyString, ...] = ()
