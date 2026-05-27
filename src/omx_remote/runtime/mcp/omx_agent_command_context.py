from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandStep,
    CommandStepCommand,
)


def context_lines(
    objective: str | None = None,
    topic: str | None = None,
    rubric: str | None = None,
    slug: str | None = None,
    prd_path: str | None = None,
    notes: str | None = None,
) -> tuple[str, ...]:
    """Build extra context lines for command prompts.

    Args:
        objective [str | None]: User objective.
        topic [str | None]: Research topic.
        rubric [str | None]: Research rubric.
        slug [str | None]: Durable run slug.
        prd_path [str | None]: PRD or brief path.
        notes [str | None]: Additional notes.

    Returns:
        tuple[str, ...]: Non-empty context lines.
    """
    raw_lines: tuple[tuple[str, str | None], ...] = (
        ("Objective", objective),
        ("Topic", topic),
        ("Rubric", rubric),
        ("Slug", slug),
        ("PRD or brief path", prd_path),
        ("Notes", notes),
    )
    lines: list[str] = []
    for label, value in raw_lines:
        if value is None:
            continue
        stripped = value.strip()
        if not stripped:
            continue
        lines.append(f"- {label}: {stripped}")
    built_lines: tuple[str, ...] = tuple(lines)
    return built_lines


def _append_context(prompt: str | None, lines: tuple[str, ...]) -> str | None:
    """Append MCP tool context to a command step prompt.

    Args:
        prompt [str | None]: Existing inline prompt.
        lines [tuple[str, ...]]: Context lines.

    Returns:
        str | None: Prompt with context appended when applicable.
    """
    if prompt is None:
        missing_prompt: None = None
        return missing_prompt
    if not lines:
        unchanged_prompt = prompt
        return unchanged_prompt
    context_block = "\n".join(lines)
    updated_prompt = f"{prompt}\n\nMCP tool-supplied context:\n{context_block}"
    return updated_prompt


def _step_with_context(
    step: CommandStep,
    lines: tuple[str, ...],
    prd_path: str | None,
) -> CommandStep:
    """Return one command step with optional MCP context applied.

    Args:
        step [CommandStep]: Original step.
        lines [tuple[str, ...]]: Context lines to append.
        prd_path [str | None]: Optional PRD path for Ultragoal brief handoff.

    Returns:
        CommandStep: Updated immutable step copy.
    """
    inline_prompt = _append_context(step.inline_prompt, lines)
    brief_file = step.brief_file
    if prd_path is not None and step.command == CommandStepCommand.OMX_ULTRAGOAL:
        brief_file = prd_path
    updated_step = step.model_copy(
        update={
            "inline_prompt": inline_prompt,
            "brief_file": brief_file,
        }
    )
    return updated_step


def recipe_with_context(
    recipe: CommandRecipe,
    objective: str | None = None,
    topic: str | None = None,
    rubric: str | None = None,
    slug: str | None = None,
    prd_path: str | None = None,
    notes: str | None = None,
) -> CommandRecipe:
    """Return a command recipe with per-call MCP context embedded in prompts.

    Args:
        recipe [CommandRecipe]: Original recipe.
        objective [str | None]: User objective.
        topic [str | None]: Research topic.
        rubric [str | None]: Research rubric.
        slug [str | None]: Durable run slug.
        prd_path [str | None]: PRD or brief path.
        notes [str | None]: Additional notes.

    Returns:
        CommandRecipe: Updated recipe.
    """
    lines = context_lines(
        objective=objective,
        topic=topic,
        rubric=rubric,
        slug=slug,
        prd_path=prd_path,
        notes=notes,
    )
    if not lines and prd_path is None:
        unchanged_recipe = recipe
        return unchanged_recipe
    steps = tuple(
        _step_with_context(step, lines, prd_path=prd_path) for step in recipe.steps
    )
    updated_recipe = recipe.model_copy(update={"steps": steps})
    return updated_recipe
