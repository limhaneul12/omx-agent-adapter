from omx_remote.schemas.commands.command_execution_schemas import (
    CommandFailureClassification,
    CommandFailureKind,
    CommandRecoveryAction,
    CommandRetryDecision,
)

_NON_RETRYABLE_KINDS: tuple[CommandFailureKind, ...] = (
    CommandFailureKind.MISSING_TOOL,
    CommandFailureKind.INVALID_COMMAND,
    CommandFailureKind.PERMISSION_OR_POLICY_BLOCK,
    CommandFailureKind.DIRTY_WORKTREE,
)


class RetryPolicy:
    """Bounded retry policy for actual command steps."""

    def __init__(self, max_attempts: int = 2) -> None:
        """Create a retry policy with bounded attempts.

        Args:
            max_attempts: See function signature."""
        self._max_attempts = max(1, max_attempts)

    def decide(
        self,
        classification: CommandFailureClassification,
        attempt: int,
    ) -> CommandRetryDecision:
        """Choose whether to retry or move to recovery/final failure.

        Args:
            classification: See function signature.
            attempt: See function signature.

        Returns:
            See function return annotation."""
        if classification.kind in _NON_RETRYABLE_KINDS or not classification.retryable:
            decision = CommandRetryDecision(
                action=CommandRecoveryAction.FINAL_FAIL,
                reason=f"{classification.kind} is not retryable.",
                attempt=attempt,
                max_attempts=self._max_attempts,
            )
            return decision
        if attempt < self._max_attempts:
            retry = CommandRetryDecision(
                action=CommandRecoveryAction.RETRY_STEP,
                reason="Retrying failed step before attempting recovery.",
                attempt=attempt,
                max_attempts=self._max_attempts,
            )
            return retry

        recovery = CommandRetryDecision(
            action=CommandRecoveryAction.WRITE_HANDOFF,
            reason="Retry budget exhausted; writing recovery evidence.",
            attempt=attempt,
            max_attempts=self._max_attempts,
        )
        return recovery
