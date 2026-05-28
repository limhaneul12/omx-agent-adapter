from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandStep,
    CommandStepCommand,
)


def codex_step(
    prompt: str,
    output_last_message: str | None = None,
    expected_artifacts: tuple[str, ...] = (),
    search: bool = False,
) -> CommandStep:
    """Build a read-only Codex exec recipe step.

    Args:
        prompt: See function signature.
        output_last_message: See function signature.
        expected_artifacts: See function signature.
        search: See function signature.

    Returns:
        See function return annotation."""
    step = CommandStep(
        command=CommandStepCommand.CODEX_EXEC,
        codex_search=search,
        codex_sandbox="read-only",
        inline_prompt=prompt,
        output_last_message=output_last_message,
        expected_artifacts=expected_artifacts,
    )
    return step


def prompt_step(
    prompt: str,
    expected_artifacts: tuple[str, ...] = (),
) -> CommandStep:
    """Build a prompt-only recipe step.

    Args:
        prompt: See function signature.
        expected_artifacts: See function signature.

    Returns:
        See function return annotation."""
    step = CommandStep(
        command=CommandStepCommand.PROMPT_ONLY,
        inline_prompt=prompt,
        expected_artifacts=expected_artifacts,
    )
    return step


def local_step(argv: tuple[str, ...]) -> CommandStep:
    """Build a local command preview step.

    Args:
        argv: See function signature.

    Returns:
        See function return annotation."""
    step = CommandStep(command=CommandStepCommand.LOCAL, argv=argv)
    return step
