from pathlib import Path

from omx_remote.runtime.commands.actual_run_record_writer import (
    ActualRunPaths,
    initialize_actual_run,
    now_iso,
    persist_actual_result,
    persist_initial_run_record,
    write_json_artifact,
)
from omx_remote.runtime.commands.agent_autonomy_policy import AgentAutonomyPolicy
from omx_remote.runtime.commands.artifact_verifier import ArtifactVerifier
from omx_remote.runtime.commands.command_output_redaction import (
    redact_argv,
    redact_text,
)
from omx_remote.runtime.commands.command_placeholder_resolution import (
    ExecutionPlaceholderState,
    extract_route_from_stdout,
    resolve_artifact_path,
    step_argv,
)
from omx_remote.runtime.commands.failure_classification import FailureClassifier
from omx_remote.runtime.commands.prompt_artifact_materializer import (
    materialize_expected_artifacts,
)
from omx_remote.runtime.commands.recovery_strategy import (
    append_recovery_note,
    render_recovery_note,
)
from omx_remote.runtime.commands.retry_policy import RetryPolicy
from omx_remote.runtime.commands.subprocess_attempt_runner import (
    SubprocessAttemptOutcome,
    run_subprocess,
    write_attempt,
)
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandActualRunResult,
    CommandActualRunStatus,
    CommandArtifactCheck,
    CommandAutonomyDecision,
    CommandAutonomyDecisionKind,
    CommandAutonomyMode,
    CommandFailureClassification,
    CommandFailureKind,
    CommandRecoveryAction,
    CommandRetryDecision,
    CommandStepAttempt,
    CommandStepExecutionResult,
    CommandStepExecutionStatus,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandExecutionPlan,
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
_STOPPING_STATUSES: frozenset[CommandStepExecutionStatus] = frozenset(
    {
        CommandStepExecutionStatus.FAILED,
        CommandStepExecutionStatus.BLOCKED,
        CommandStepExecutionStatus.REQUIRES_AGENT_ACTION,
    }
)


def _write_step_json(paths: ActualRunPaths, step: CommandPlanStep) -> None:
    """Persist a planned step next to actual step attempts.

    Args:
        paths: See function signature.
        step: See function signature."""
    step_dir = paths.run_dir / "steps" / f"{step.index:03d}"
    step_dir.mkdir(parents=True, exist_ok=True)
    write_json_artifact(step_dir / "step.json", step.model_dump(mode="json"))


def _step_should_handoff(step: CommandPlanStep) -> bool:
    """Return whether a runtime step needs a handoff instead of blind launch.

    Args:
        step: See function signature.

    Returns:
        See function return annotation."""
    should_handoff: bool = step.command in _RUNTIME_HANDOFF_COMMANDS
    return should_handoff


def _missing_artifact_classification(
    checks: tuple[CommandArtifactCheck, ...],
) -> CommandFailureClassification | None:
    """Classify missing required artifacts after an otherwise successful step.

    Args:
        checks: See function signature.

    Returns:
        See function return annotation."""
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


class CommandExecutor:
    """Execute typed command plans and write actual run records."""

    def __init__(self, max_attempts: int = 2, timeout_seconds: float = 120.0) -> None:
        """Create a command executor with bounded retries and timeouts.

        Args:
            max_attempts: See function signature.
            timeout_seconds: See function signature."""
        self._policy = AgentAutonomyPolicy()
        self._classifier = FailureClassifier()
        self._retry_policy = RetryPolicy(max_attempts=max_attempts)
        self._artifact_verifier = ArtifactVerifier()
        self._timeout_seconds = timeout_seconds

    def execute(
        self,
        plan: CommandExecutionPlan,
        cwd: str | Path,
        autonomy_mode: CommandAutonomyMode = CommandAutonomyMode.AGENT,
        task_text: str | None = None,
        timestamp: str | None = None,
    ) -> CommandActualRunResult:
        """Execute a command plan and persist a typed actual result.

        Args:
            plan: See function signature.
            cwd: See function signature.
            autonomy_mode: See function signature.
            task_text: See function signature.
            timestamp: See function signature.

        Returns:
            See function return annotation."""
        cwd_path: Path = Path(cwd).resolve()
        started_at: str = now_iso()
        paths: ActualRunPaths = initialize_actual_run(
            plan, cwd_path, timestamp=timestamp
        )
        decision: CommandAutonomyDecision = self._policy.decide(plan, autonomy_mode)
        write_json_artifact(
            paths.autonomy_decision_path, decision.model_dump(mode="json")
        )
        persist_initial_run_record(plan, paths, cwd_path, started_at)
        state = ExecutionPlaceholderState(
            run_id=paths.run_id,
            command_id=plan.command_id,
            task_text=task_text or plan.description,
        )
        if decision.decision != CommandAutonomyDecisionKind.ALLOW:
            result = self._blocked_result(plan, paths, cwd_path, started_at, decision)
            persist_actual_result(plan, paths, cwd_path, result, decision)
            return result

        step_results: list[CommandStepExecutionResult] = []
        for step in plan.steps:
            step_result = self._execute_step(step, paths, cwd_path, state)
            step_results.append(step_result)
            if step_result.status in _STOPPING_STATUSES:
                break
        result = self._final_result(
            plan, paths, cwd_path, started_at, decision, tuple(step_results)
        )
        persist_actual_result(plan, paths, cwd_path, result, decision)
        return result

    def _execute_step(
        self,
        step: CommandPlanStep,
        paths: ActualRunPaths,
        cwd: Path,
        state: ExecutionPlaceholderState,
    ) -> CommandStepExecutionResult:
        """Implement execute step behavior.

        Args:
            step: See function signature.
            paths: See function signature.
            cwd: See function signature.
            state: See function signature.

        Returns:
            See function return annotation."""
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
        """Implement execute prompt step behavior.

        Args:
            step: See function signature.
            paths: See function signature.
            cwd: See function signature.
            state: See function signature.

        Returns:
            See function return annotation."""
        materialized_paths = materialize_expected_artifacts(step, paths, state, cwd)
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
        """Implement execute subprocess step behavior.

        Args:
            step: See function signature.
            paths: See function signature.
            cwd: See function signature.
            state: See function signature.

        Returns:
            See function return annotation."""
        attempts: list[CommandStepAttempt] = []
        retry_decisions: list[CommandRetryDecision] = []
        artifact_checks: tuple[CommandArtifactCheck, ...] = ()
        last_classification: CommandFailureClassification | None = None
        attempt_number = 1
        while True:
            outcome = run_subprocess(
                step_argv(step, cwd, state), cwd, self._timeout_seconds
            )
            classification = self._classify_outcome(outcome)
            attempt = write_attempt(
                paths, step.index, attempt_number, outcome, classification
            )
            attempts.append(attempt)
            if classification is None:
                artifact_checks = self._check_expected_artifacts(step, state)
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
        result = self._failed_step_result(
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
            outcome: See function signature.

        Returns:
            See function return annotation."""
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
    ) -> tuple[CommandArtifactCheck, ...]:
        """Verify expected artifacts without manufacturing subprocess outputs.

        Args:
            step: See function signature.
            state: See function signature.

        Returns:
            See function return annotation."""
        artifact_paths: tuple[Path, ...] = tuple(
            resolve_artifact_path(artifact, state)
            for artifact in step.expected_artifacts
        )
        if not artifact_paths:
            empty_checks: tuple[CommandArtifactCheck, ...] = ()
            return empty_checks
        checks = self._artifact_verifier.check_many(artifact_paths)
        return checks

    def _failed_step_result(
        self,
        step: CommandPlanStep,
        attempts: list[CommandStepAttempt],
        classification: CommandFailureClassification,
        retry_decisions: list[CommandRetryDecision],
        artifact_checks: tuple[CommandArtifactCheck, ...] = (),
    ) -> CommandStepExecutionResult:
        """Implement failed step result behavior.

        Args:
            step: See function signature.
            attempts: See function signature.
            classification: See function signature.
            retry_decisions: See function signature.
            artifact_checks: See function signature.

        Returns:
            See function return annotation."""
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

    def _blocked_result(
        self,
        plan: CommandExecutionPlan,
        paths: ActualRunPaths,
        cwd: Path,
        started_at: str,
        decision: CommandAutonomyDecision,
    ) -> CommandActualRunResult:
        """Implement blocked result behavior.

        Args:
            plan: See function signature.
            paths: See function signature.
            cwd: See function signature.
            started_at: See function signature.
            decision: See function signature.

        Returns:
            See function return annotation."""
        finished_at: str = now_iso()
        result = CommandActualRunResult(
            run_id=paths.run_id,
            command_id=plan.command_id,
            qualified_id=plan.qualified_id,
            cwd=str(cwd),
            dry_run=False,
            status=CommandActualRunStatus.BLOCKED,
            started_at=started_at,
            finished_at=finished_at,
            run_dir=str(paths.run_dir),
            plan_path=str(paths.plan_path),
            autonomy_decision_path=str(paths.autonomy_decision_path),
            result_path=str(paths.result_path),
            artifacts_path=str(paths.artifacts_path),
            recovery_path=str(paths.recovery_path),
            autonomy_decision=decision,
            steps=(),
            artifact_checks=(),
            blocked_reasons=decision.blocked_reasons,
        )
        return result

    def _final_result(
        self,
        plan: CommandExecutionPlan,
        paths: ActualRunPaths,
        cwd: Path,
        started_at: str,
        decision: CommandAutonomyDecision,
        step_results: tuple[CommandStepExecutionResult, ...],
    ) -> CommandActualRunResult:
        """Implement final result behavior.

        Args:
            plan: See function signature.
            paths: See function signature.
            cwd: See function signature.
            started_at: See function signature.
            decision: See function signature.
            step_results: See function signature.

        Returns:
            See function return annotation."""
        finished_at: str = now_iso()
        artifact_checks: tuple[CommandArtifactCheck, ...] = tuple(
            check for step in step_results for check in step.artifact_checks
        )
        status = _actual_status(step_results)
        result = CommandActualRunResult(
            run_id=paths.run_id,
            command_id=plan.command_id,
            qualified_id=plan.qualified_id,
            cwd=str(cwd),
            dry_run=False,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            run_dir=str(paths.run_dir),
            plan_path=str(paths.plan_path),
            autonomy_decision_path=str(paths.autonomy_decision_path),
            result_path=str(paths.result_path),
            artifacts_path=str(paths.artifacts_path),
            recovery_path=str(paths.recovery_path),
            autonomy_decision=decision,
            steps=step_results,
            artifact_checks=artifact_checks,
            blocked_reasons=(),
        )
        return result


def _actual_status(
    step_results: tuple[CommandStepExecutionResult, ...],
) -> CommandActualRunStatus:
    """Summarize step statuses into an actual run status.

    Args:
        step_results: See function signature.

    Returns:
        See function return annotation."""
    if any(step.status == CommandStepExecutionStatus.FAILED for step in step_results):
        status = CommandActualRunStatus.FAILED
        return status
    if any(step.status == CommandStepExecutionStatus.BLOCKED for step in step_results):
        status = CommandActualRunStatus.BLOCKED
        return status
    if any(
        step.status == CommandStepExecutionStatus.REQUIRES_AGENT_ACTION
        for step in step_results
    ):
        status = CommandActualRunStatus.REQUIRES_AGENT_ACTION
        return status
    status = CommandActualRunStatus.SUCCEEDED
    return status
