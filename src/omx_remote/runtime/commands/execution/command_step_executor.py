from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.artifacts.artifact_verifier import ArtifactVerifier
from omx_remote.runtime.commands.artifacts.command_artifact_path_policy import (
    validate_materialized_artifact_paths,
)
from omx_remote.runtime.commands.artifacts.prompt_artifact_materializer import (
    materialize_expected_artifacts,
)
from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.commands.execution.subprocess_attempt_runner import (
    SubprocessAttemptOutcome,
    run_subprocess,
    write_attempt,
)
from omx_remote.runtime.commands.rendering.command_output_redaction import (
    redact_argv,
    redact_text,
)
from omx_remote.runtime.commands.rendering.command_placeholder_resolution import (
    ExecutionPlaceholderState,
    extract_route_from_stdout,
    resolve_artifact_path,
    step_argv,
)
from omx_remote.runtime.commands.resilience.failure_classification import (
    FailureClassifier,
)
from omx_remote.runtime.commands.resilience.recovery_strategy import (
    append_recovery_note,
    render_recovery_note,
)
from omx_remote.runtime.commands.resilience.retry_policy import RetryPolicy
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandArtifactCheck,
    CommandFailureClassification,
    CommandFailureKind,
    CommandRecoveryAction,
    CommandRetryDecision,
    CommandStepAttempt,
    CommandStepExecutionResult,
    CommandStepExecutionStatus,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandPlanStep,
    CommandStepCommand,
)

_RUNTIME_HANDOFF_COMMANDS: frozenset[CommandStepCommand] = frozenset(
    {
        CommandStepCommand.OMX_EXEC,
        CommandStepCommand.OMX_ULTRAGOAL,
        CommandStepCommand.OMX_TEAM,
        CommandStepCommand.OMX_RALPH,
    }
)
_MIN_CODEX_EXEC_TIMEOUT_SECONDS = 300.0


def _write_step_json(paths: ActualRunPaths, step: CommandPlanStep) -> None:
    """Persist a planned step next to actual step attempts.

    Args:
        paths [ActualRunPaths]: Actual run path bundle.
        step [CommandPlanStep]: Planned step to persist.
    """
    step_dir = paths.run_dir / "steps" / f"{step.index:03d}"
    step_dir.mkdir(parents=True, exist_ok=True)
    write_redacted_json_artifact(step_dir / "step.json", step)


def _step_should_handoff(step: CommandPlanStep) -> bool:
    """Return whether a runtime step needs a handoff instead of blind launch.

    Args:
        step [CommandPlanStep]: Step to inspect.

    Returns:
        bool: Whether the step requires an agent/runtime handoff.
    """
    should_handoff: bool = step.command in _RUNTIME_HANDOFF_COMMANDS
    return should_handoff


def _missing_artifact_classification(
    checks: tuple[CommandArtifactCheck, ...],
) -> CommandFailureClassification | None:
    """Classify missing required artifacts after an otherwise successful step.

    Args:
        checks [tuple[CommandArtifactCheck, ...]]: Artifact verification checks.

    Returns:
        CommandFailureClassification | None: Missing-artifact failure when present.
    """
    missing_paths: tuple[str, ...] = tuple(
        check.path for check in checks if check.required and not check.exists
    )
    if not missing_paths:
        no_failure: None = None
        return no_failure
    classification = CommandFailureClassification(
        kind=CommandFailureKind.MISSING_ARTIFACT,
        reason=f"Missing expected artifacts: {', '.join(missing_paths)}",
        retryable=True,
    )
    return classification


def _validated_expected_artifact_paths(
    step: CommandPlanStep,
    state: ExecutionPlaceholderState,
    cwd: Path,
) -> tuple[Path, ...]:
    """Resolve and validate every expected artifact before side effects.

    Args:
        step [CommandPlanStep]: Step with expected artifact templates.
        state [ExecutionPlaceholderState]: Placeholder resolution state.
        cwd [Path]: Repository root.

    Returns:
        tuple[Path, ...]: Validated artifact paths.
    """
    artifact_paths: tuple[Path, ...] = validate_materialized_artifact_paths(
        (
            resolve_artifact_path(artifact, state)
            for artifact in step.expected_artifacts
        ),
        cwd,
    )
    return artifact_paths


def _prepare_subprocess_artifact_directories(
    step: CommandPlanStep,
    state: ExecutionPlaceholderState,
    cwd: Path,
) -> None:
    """Create parent directories for artifacts a subprocess is expected to write.

    Args:
        step [CommandPlanStep]: Step with expected artifact templates.
        state [ExecutionPlaceholderState]: Placeholder resolution state.
        cwd [Path]: Repository root.
    """
    artifact_paths = _validated_expected_artifact_paths(step, state, cwd)
    for artifact_path in artifact_paths:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)


def _artifact_policy_failure(error: ValueError) -> CommandFailureClassification:
    """Build a non-retryable failure for unsafe artifact paths.

    Args:
        error [ValueError]: Path-policy error raised while preparing artifacts.

    Returns:
        CommandFailureClassification: Failure classification for the blocked path.
    """
    classification = CommandFailureClassification(
        kind=CommandFailureKind.PERMISSION_OR_POLICY_BLOCK,
        reason=redact_text(str(error)),
        retryable=False,
    )
    return classification


def _subprocess_timeout_seconds(
    step: CommandPlanStep,
    default_timeout_seconds: float,
) -> float:
    """Return the timeout budget for one subprocess step.

    Args:
        step [CommandPlanStep]: Step being executed.
        default_timeout_seconds [float]: Default timeout budget.

    Returns:
        float: Timeout budget for the step.
    """
    if step.command == CommandStepCommand.CODEX_EXEC:
        timeout_seconds = max(
            default_timeout_seconds,
            _MIN_CODEX_EXEC_TIMEOUT_SECONDS,
        )
        return timeout_seconds
    return default_timeout_seconds


def _failed_step_result(
    step: CommandPlanStep,
    attempts: list[CommandStepAttempt],
    classification: CommandFailureClassification,
    retry_decisions: list[CommandRetryDecision],
    artifact_checks: tuple[CommandArtifactCheck, ...] = (),
) -> CommandStepExecutionResult:
    """Build a failed step result.

    Args:
        step [CommandPlanStep]: Failed step.
        attempts [list[CommandStepAttempt]]: Persisted subprocess attempts.
        classification [CommandFailureClassification]: Failure reason.
        retry_decisions [list[CommandRetryDecision]]: Retry decisions.
        artifact_checks [tuple[CommandArtifactCheck, ...]]: Artifact checks.

    Returns:
        CommandStepExecutionResult: Failed step result.
    """
    result = CommandStepExecutionResult(
        index=step.index,
        command=step.command,
        status=CommandStepExecutionStatus.FAILED,
        attempts=tuple(attempts),
        artifact_checks=artifact_checks,
        failure=classification,
        retry_decisions=tuple(retry_decisions),
    )
    return result


class CommandStepExecutor:
    """Execute individual command plan steps."""

    def __init__(
        self,
        classifier: FailureClassifier,
        retry_policy: RetryPolicy,
        artifact_verifier: ArtifactVerifier,
        timeout_seconds: float,
    ) -> None:
        """Create a step executor. Args: classifier, retry_policy, artifact_verifier, timeout_seconds."""
        self._classifier = classifier
        self._retry_policy = retry_policy
        self._artifact_verifier = artifact_verifier
        self._timeout_seconds = timeout_seconds

    def execute_step(
        self,
        step: CommandPlanStep,
        paths: ActualRunPaths,
        cwd: Path,
        state: ExecutionPlaceholderState,
    ) -> CommandStepExecutionResult:
        """Execute one planned step.

        Args:
            step [CommandPlanStep]: Step to execute.
            paths [ActualRunPaths]: Actual run path bundle.
            cwd [Path]: Repository root.
            state [ExecutionPlaceholderState]: Placeholder state for this run.

        Returns:
            CommandStepExecutionResult: Step execution result.
        """
        _write_step_json(paths, step)
        if step.command == CommandStepCommand.PROMPT_ONLY or _step_should_handoff(step):
            result = self._execute_prompt_step(step, paths, cwd, state)
            return result
        result = self._execute_subprocess_step(step, paths, cwd, state)
        return result

    def _execute_prompt_step(
        self,
        step: CommandPlanStep,
        paths: ActualRunPaths,
        cwd: Path,
        state: ExecutionPlaceholderState,
    ) -> CommandStepExecutionResult:
        """Execute a prompt-only or runtime-handoff step.

        Args:
            step [CommandPlanStep]: Step to execute.
            paths [ActualRunPaths]: Actual run path bundle.
            cwd [Path]: Repository root.
            state [ExecutionPlaceholderState]: Placeholder state for this run.

        Returns:
            CommandStepExecutionResult: Handoff step result.
        """
        try:
            materialized_paths = materialize_expected_artifacts(step, paths, state, cwd)
        except ValueError as error:
            classification = _artifact_policy_failure(error)
            result = _failed_step_result(step, [], classification, [])
            return result
        checks = self._artifact_verifier.check_many(materialized_paths)
        result = CommandStepExecutionResult(
            index=step.index,
            command=step.command,
            status=CommandStepExecutionStatus.REQUIRES_AGENT_ACTION,
            attempts=(),
            artifact_checks=checks,
            handoff_path=str(materialized_paths[0]),
            failure=None,
            retry_decisions=(),
        )
        return result

    def _execute_subprocess_step(
        self,
        step: CommandPlanStep,
        paths: ActualRunPaths,
        cwd: Path,
        state: ExecutionPlaceholderState,
    ) -> CommandStepExecutionResult:
        """Execute a local subprocess step with retries.

        Args:
            step [CommandPlanStep]: Step to execute.
            paths [ActualRunPaths]: Actual run path bundle.
            cwd [Path]: Repository root.
            state [ExecutionPlaceholderState]: Placeholder state for this run.

        Returns:
            CommandStepExecutionResult: Subprocess step result.
        """
        attempts: list[CommandStepAttempt] = []
        retry_decisions: list[CommandRetryDecision] = []
        artifact_checks: tuple[CommandArtifactCheck, ...] = ()
        last_classification: CommandFailureClassification | None = None
        attempt_number = 1
        while True:
            try:
                _prepare_subprocess_artifact_directories(step, state, cwd)
            except ValueError as error:
                classification = _artifact_policy_failure(error)
                result = _failed_step_result(
                    step,
                    attempts,
                    classification,
                    retry_decisions,
                    artifact_checks,
                )
                return result
            outcome = run_subprocess(
                step_argv(step, cwd, state),
                cwd,
                _subprocess_timeout_seconds(step, self._timeout_seconds),
            )
            classification = self._classify_outcome(outcome)
            attempt = write_attempt(
                paths, step.index, attempt_number, outcome, classification
            )
            attempts.append(attempt)
            if classification is None:
                artifact_checks = self._check_expected_artifacts(step, state, cwd)
                classification = _missing_artifact_classification(artifact_checks)
            if classification is None:
                extract_route_from_stdout(outcome.stdout, state)
                result = CommandStepExecutionResult(
                    index=step.index,
                    command=step.command,
                    status=CommandStepExecutionStatus.SUCCEEDED,
                    attempts=tuple(attempts),
                    artifact_checks=artifact_checks,
                    failure=None,
                    retry_decisions=tuple(retry_decisions),
                )
                return result

            last_classification = classification
            retry_decision = self._retry_policy.decide(classification, attempt_number)
            retry_decisions.append(retry_decision)
            if retry_decision.action != CommandRecoveryAction.RETRY_STEP:
                append_recovery_note(
                    paths.recovery_path,
                    render_recovery_note(step, classification, tuple(retry_decisions)),
                )
                break
            attempt_number += 1

        if last_classification is None:
            raise RuntimeError("subprocess execution ended without success or failure")
        result = _failed_step_result(
            step,
            attempts,
            last_classification,
            retry_decisions,
            artifact_checks,
        )
        return result

    def _classify_outcome(
        self,
        outcome: SubprocessAttemptOutcome,
    ) -> CommandFailureClassification | None:
        """Classify failed subprocess output using redacted persisted evidence.

        Args:
            outcome [SubprocessAttemptOutcome]: Subprocess outcome.

        Returns:
            CommandFailureClassification | None: Failure classification.
        """
        if outcome.exit_code == 0 and not outcome.timed_out:
            no_failure: None = None
            return no_failure
        classification = self._classifier.classify(
            redact_argv(outcome.argv),
            outcome.exit_code,
            redact_text(outcome.stderr),
            redact_text(outcome.stdout),
            timed_out=outcome.timed_out,
        )
        return classification

    def _check_expected_artifacts(
        self,
        step: CommandPlanStep,
        state: ExecutionPlaceholderState,
        cwd: Path,
    ) -> tuple[CommandArtifactCheck, ...]:
        """Verify expected artifacts without manufacturing subprocess outputs.

        Args:
            step [CommandPlanStep]: Step whose artifacts should be checked.
            state [ExecutionPlaceholderState]: Placeholder state for this run.
            cwd [Path]: Repository root.

        Returns:
            tuple[CommandArtifactCheck, ...]: Artifact checks.
        """
        artifact_paths = _validated_expected_artifact_paths(step, state, cwd)
        if not artifact_paths:
            empty_checks: tuple[CommandArtifactCheck, ...] = ()
            return empty_checks
        checks = self._artifact_verifier.check_many(artifact_paths)
        return checks
