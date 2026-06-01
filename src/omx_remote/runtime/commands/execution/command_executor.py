from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
    initialize_actual_run,
    persist_actual_result,
    persist_initial_run_record,
)
from omx_remote.runtime.commands.artifacts.artifact_verifier import ArtifactVerifier
from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.commands.execution.agent_autonomy_policy import (
    AgentAutonomyPolicy,
)
from omx_remote.runtime.commands.execution.command_step_executor import (
    CommandStepExecutor,
)
from omx_remote.runtime.commands.rendering.command_placeholder_resolution import (
    ExecutionPlaceholderState,
)
from omx_remote.runtime.commands.resilience.failure_classification import (
    FailureClassifier,
)
from omx_remote.runtime.commands.resilience.retry_policy import RetryPolicy
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandActualRunResult,
    CommandActualRunStatus,
    CommandArtifactCheck,
    CommandAutonomyDecision,
    CommandAutonomyDecisionKind,
    CommandAutonomyMode,
    CommandStepExecutionResult,
    CommandStepExecutionStatus,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.shared.utils.runtime_identity import utcnow_text

_STOPPING_STATUSES: frozenset[CommandStepExecutionStatus] = frozenset(
    {
        CommandStepExecutionStatus.FAILED,
        CommandStepExecutionStatus.BLOCKED,
        CommandStepExecutionStatus.REQUIRES_AGENT_ACTION,
    }
)


class CommandExecutor:
    """Execute typed command plans and write actual run records."""

    def __init__(self, max_attempts: int = 2, timeout_seconds: float = 120.0) -> None:
        """Create a command executor with bounded retries and timeouts.

        Args:
            max_attempts [int]: Maximum retry attempts for subprocess steps.
            timeout_seconds [float]: Default subprocess timeout.
        """
        classifier = FailureClassifier()
        retry_policy = RetryPolicy(max_attempts=max_attempts)
        artifact_verifier = ArtifactVerifier()
        self._policy = AgentAutonomyPolicy()
        self._step_executor = CommandStepExecutor(
            classifier=classifier,
            retry_policy=retry_policy,
            artifact_verifier=artifact_verifier,
            timeout_seconds=timeout_seconds,
        )

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
            plan [CommandExecutionPlan]: Dry-run plan to execute.
            cwd [str | Path]: Repository root.
            autonomy_mode [CommandAutonomyMode]: Autonomy policy mode.
            task_text [str | None]: Optional task text for artifact placeholders.
            timestamp [str | None]: Optional run timestamp override.

        Returns:
            CommandActualRunResult: Persisted actual run result.
        """
        cwd_path: Path = Path(cwd).resolve()
        started_at: str = utcnow_text()
        paths: ActualRunPaths = initialize_actual_run(
            plan, cwd_path, timestamp=timestamp
        )
        decision: CommandAutonomyDecision = self._policy.decide(plan, autonomy_mode)
        write_redacted_json_artifact(
            paths.autonomy_decision_path, decision
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
            step_result = self._step_executor.execute_step(
                step,
                paths,
                cwd_path,
                state,
            )
            step_results.append(step_result)
            if step_result.status in _STOPPING_STATUSES:
                break
        result = self._final_result(
            plan, paths, cwd_path, started_at, decision, tuple(step_results)
        )
        persist_actual_result(plan, paths, cwd_path, result, decision)
        return result

    def _blocked_result(
        self,
        plan: CommandExecutionPlan,
        paths: ActualRunPaths,
        cwd: Path,
        started_at: str,
        decision: CommandAutonomyDecision,
    ) -> CommandActualRunResult:
        """Build the actual result for an autonomy-policy block.

        Args:
            plan [CommandExecutionPlan]: Plan that was blocked.
            paths [ActualRunPaths]: Actual run path bundle.
            cwd [Path]: Repository root.
            started_at [str]: Run start timestamp.
            decision [CommandAutonomyDecision]: Blocking autonomy decision.

        Returns:
            CommandActualRunResult: Blocked actual run result.
        """
        finished_at: str = utcnow_text()
        result = CommandActualRunResult(
            run_id=paths.run_id,
            command_id=plan.command_id,
            qualified_id=plan.qualified_id,
            cwd=str(cwd),
            dry_run=False,
            runtime_options=plan.runtime_options,
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
        """Build the final actual result from executed step results.

        Args:
            plan [CommandExecutionPlan]: Plan that was executed.
            paths [ActualRunPaths]: Actual run path bundle.
            cwd [Path]: Repository root.
            started_at [str]: Run start timestamp.
            decision [CommandAutonomyDecision]: Autonomy decision.
            step_results [tuple[CommandStepExecutionResult, ...]]: Step results.

        Returns:
            CommandActualRunResult: Final actual run result.
        """
        finished_at: str = utcnow_text()
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
            runtime_options=plan.runtime_options,
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
        step_results [tuple[CommandStepExecutionResult, ...]]: Step results.

    Returns:
        CommandActualRunStatus: Aggregate actual run status.
    """
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
