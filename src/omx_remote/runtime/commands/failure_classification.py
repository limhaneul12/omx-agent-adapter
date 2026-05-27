from collections.abc import Sequence

from omx_remote.schemas.commands.command_execution_schemas import (
    CommandFailureClassification,
    CommandFailureKind,
)


def _text_contains_any(value: str, markers: tuple[str, ...]) -> bool:
    """Implement text contains any behavior.

    Args:
        value: See function signature.
        markers: See function signature.

    Returns:
        See function return annotation."""
    normalized_value: str = value.lower()
    contains_marker: bool = any(marker in normalized_value for marker in markers)
    return contains_marker


class FailureClassifier:
    """Classify subprocess/tool failures into retryable command failure kinds."""

    def classify(
        self,
        argv: Sequence[str],
        exit_code: int | None,
        stderr: str,
        stdout: str,
        timed_out: bool = False,
    ) -> CommandFailureClassification:
        """Classify one failed attempt.

        Args:
            argv: See function signature.
            exit_code: See function signature.
            stderr: See function signature.
            stdout: See function signature.
            timed_out: See function signature.

        Returns:
            See function return annotation."""
        command_text: str = " ".join(argv)
        output_text: str = f"{stdout}\n{stderr}"
        if timed_out:
            classification = CommandFailureClassification(
                kind=CommandFailureKind.TIMEOUT,
                reason=f"Command timed out: {command_text}",
                retryable=True,
            )
            return classification
        if exit_code == 127 or _text_contains_any(
            output_text,
            ("command not found", "no such file or directory", "not found"),
        ):
            classification = CommandFailureClassification(
                kind=CommandFailureKind.MISSING_TOOL,
                reason=f"Required tool was not available for: {command_text}",
                retryable=False,
            )
            return classification
        if _text_contains_any(
            output_text, ("network", "temporarily unavailable", "timeout")
        ):
            classification = CommandFailureClassification(
                kind=CommandFailureKind.TRANSIENT_NETWORK,
                reason=f"Transient external failure while running: {command_text}",
                retryable=True,
            )
            return classification
        if any(part == "ruff" for part in argv) or "ruff check" in command_text:
            classification = CommandFailureClassification(
                kind=CommandFailureKind.LINT_FAILURE,
                reason=f"Lint command failed: {command_text}",
                retryable=True,
            )
            return classification
        if any(part == "pytest" for part in argv):
            classification = CommandFailureClassification(
                kind=CommandFailureKind.TEST_FAILURE,
                reason=f"Test command failed: {command_text}",
                retryable=True,
            )
            return classification
        if _text_contains_any(output_text, ("dirty worktree", "uncommitted changes")):
            classification = CommandFailureClassification(
                kind=CommandFailureKind.DIRTY_WORKTREE,
                reason=f"Dirty worktree guard blocked: {command_text}",
                retryable=False,
            )
            return classification
        if exit_code is None:
            classification = CommandFailureClassification(
                kind=CommandFailureKind.INVALID_COMMAND,
                reason=f"Command could not be started: {command_text}",
                retryable=False,
            )
            return classification

        classification = CommandFailureClassification(
            kind=CommandFailureKind.UNKNOWN_FAILURE,
            reason=f"Command exited with {exit_code}: {command_text}",
            retryable=True,
        )
        return classification
