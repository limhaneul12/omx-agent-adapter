from pathlib import Path

from omx_remote.runtime.commands.rendering.command_output_redaction import (
    redact_argv,
    redact_text,
)
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandFailureClassification,
    CommandRetryDecision,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandPlanStep


def render_recovery_note(
    step: CommandPlanStep,
    classification: CommandFailureClassification | None,
    retry_decisions: tuple[CommandRetryDecision, ...],
) -> str:
    """Render a Markdown recovery note for a step.

    Args:
        step: See function signature.
        classification: See function signature.
        retry_decisions: See function signature.

    Returns:
        See function return annotation."""
    lines: list[str] = [
        f"## Step {step.index} recovery",
        "",
        f"- command: {step.command}",
        f"- argv: `{' '.join(redact_argv(step.native_argv))}`",
    ]
    if classification is not None:
        lines.extend(
            (
                f"- failure_kind: {classification.kind}",
                f"- failure_reason: {redact_text(classification.reason)}",
                f"- retryable: {classification.retryable}",
            )
        )
    if retry_decisions:
        lines.append("")
        lines.append("### Decisions")
        lines.extend(
            f"- attempt {decision.attempt}: {decision.action} — {redact_text(decision.reason)}"
            for decision in retry_decisions
        )
    note_text: str = "\n".join(lines)
    return note_text


def append_recovery_note(path: Path, note_text: str) -> None:
    """Append one recovery note to the run-level recovery artifact.

    Args:
        path: See function signature.
        note_text: See function signature."""
    existing_text: str = path.read_text(encoding="utf-8") if path.exists() else ""
    separator: str = "\n\n" if existing_text else ""
    path.write_text(
        f"{existing_text}{separator}{redact_text(note_text)}\n",
        encoding="utf-8",
    )
