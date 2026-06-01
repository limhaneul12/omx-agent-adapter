from hashlib import sha256
from pathlib import Path

from omx_remote.runtime.commands.planning.command_runtime_options import (
    codex_runtime_argv,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CodexSandboxMode,
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)


def effective_codex_sandbox(step: CommandStep) -> CodexSandboxMode | None:
    """Return the effective sandbox for Codex exec steps.

    Args:
        step [CommandStep]: Recipe step to inspect.

    Returns:
        CodexSandboxMode | None: Effective sandbox for Codex steps.
    """
    if step.command != CommandStepCommand.CODEX_EXEC:
        no_sandbox: None = None
        return no_sandbox
    sandbox: CodexSandboxMode = step.codex_sandbox or CodexSandboxMode.READ_ONLY
    return sandbox


def resolve_command_path(cwd: str | Path | None, path_text: str) -> Path:
    """Resolve a command-owned path.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        path_text [str]: Path text from a recipe.

    Returns:
        Path: Resolved path.
    """
    candidate_path = Path(path_text)
    if candidate_path.is_absolute():
        resolved_path: Path = candidate_path
        return resolved_path

    root_path: Path = Path.cwd() if cwd is None else Path(cwd)
    resolved_path = root_path / candidate_path
    return resolved_path


def prompt_file_hash(prompt_path: Path) -> str | None:
    """Hash a prompt file when it exists.

    Args:
        prompt_path [Path]: Prompt file path.

    Returns:
        str | None: SHA-256 hex digest when the file exists.
    """
    if not prompt_path.exists():
        missing_hash: None = None
        return missing_hash

    digest: str = sha256(prompt_path.read_bytes()).hexdigest()
    return digest


def resolve_expected_artifacts(
    cwd: str | Path | None, step: CommandStep
) -> tuple[str, ...]:
    """Resolve expected artifact paths from one step.

    Args:
        cwd [str | Path | None]: Base working directory for relative artifact paths.
        step [CommandStep]: Step containing artifact declarations.

    Returns:
        tuple[str, ...]: Resolved artifact paths.
    """
    artifacts: list[str] = []
    seen_artifacts: set[str] = set()
    if step.output_last_message is not None:
        output_path: str = str(resolve_command_path(cwd, step.output_last_message))
        artifacts.append(output_path)
        seen_artifacts.add(output_path)
    for artifact in step.expected_artifacts:
        artifact_path: str = str(resolve_command_path(cwd, artifact))
        if artifact_path in seen_artifacts:
            continue
        artifacts.append(artifact_path)
        seen_artifacts.add(artifact_path)
    resolved_artifacts: tuple[str, ...] = tuple(artifacts)
    return resolved_artifacts


def apply_task_placeholder(value: str | None, task_text: str | None) -> str | None:
    """Apply only the user task placeholder for dry-run preview readability.

    Args:
        value [str | None]: Candidate recipe text.
        task_text [str | None]: Optional caller-supplied task text.

    Returns:
        str | None: Text with ``<task>`` replaced when task text is supplied.
    """
    if value is None or task_text is None:
        return value

    substituted_value: str = value.replace("<task>", task_text)
    return substituted_value


def _apply_task_placeholder_to_argv(
    argv: tuple[str, ...],
    task_text: str | None,
) -> tuple[str, ...]:
    """Apply task placeholder substitution to local argv previews.

    Args:
        argv [tuple[str, ...]]: Planned native argv values.
        task_text [str | None]: Optional caller-supplied task text.

    Returns:
        tuple[str, ...]: Argv with task placeholders substituted when supplied.
    """
    if task_text is None:
        return argv
    substituted_argv: tuple[str, ...] = tuple(
        value.replace("<task>", task_text) for value in argv
    )
    return substituted_argv


def _codex_prompt_text(
    cwd: str | Path | None,
    step: CommandStep,
    task_text: str | None,
) -> str | None:
    """Build one Codex prompt from optional template and inline task text.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        step [CommandStep]: Step to render.
        task_text [str | None]: Optional caller-supplied task text.

    Returns:
        str | None: Combined prompt text when available.
    """
    prompt_parts: list[str] = []
    if step.prompt_file is not None:
        prompt_path = resolve_command_path(cwd, step.prompt_file)
        if prompt_path.exists():
            prompt_file_text = apply_task_placeholder(
                prompt_path.read_text(encoding="utf-8"),
                task_text,
            )
            if prompt_file_text is not None:
                prompt_parts.append(prompt_file_text)
    inline_prompt: str | None = apply_task_placeholder(step.inline_prompt, task_text)
    if inline_prompt is not None:
        prompt_parts.append(inline_prompt)
    if not prompt_parts:
        no_prompt: None = None
        return no_prompt
    prompt_text: str = "\n\n".join(prompt_parts)
    return prompt_text


def _build_codex_argv(
    cwd: str | Path | None,
    step: CommandStep,
    task_text: str | None,
    runtime_options: CommandRuntimeOptions | None,
) -> tuple[str, ...]:
    """Build inspectable native argv for a Codex exec step.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        step [CommandStep]: Step to render.
        task_text [str | None]: Optional caller-supplied task text.
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        tuple[str, ...]: Native argv preview.
    """
    argv: list[str] = ["codex"]
    if step.agent is not None:
        argv.extend(["-c", f'agent_type="{step.agent}"'])
    argv.extend(codex_runtime_argv(runtime_options=runtime_options))
    if step.codex_search:
        argv.append("--search")
    argv.extend(["exec", "--json"])
    codex_sandbox = effective_codex_sandbox(step)
    if codex_sandbox is not None:
        argv.extend(["--sandbox", codex_sandbox])
    if step.output_last_message is not None:
        argv.extend(
            [
                "--output-last-message",
                str(resolve_command_path(cwd, step.output_last_message)),
            ]
        )
    prompt_text = _codex_prompt_text(cwd, step, task_text)
    if prompt_text is not None:
        argv.append(prompt_text)
    native_argv: tuple[str, ...] = tuple(argv)
    return native_argv


def _build_omx_argv(cwd: str | Path | None, step: CommandStep) -> tuple[str, ...]:
    """Build inspectable native argv for an OMX step.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        step [CommandStep]: Step to render.

    Returns:
        tuple[str, ...]: Native argv preview.
    """
    if step.command == CommandStepCommand.OMX_ULTRAGOAL:
        brief_path_text: str | None = step.brief_file or step.prompt_file
        if brief_path_text is not None:
            native_argv = (
                "omx",
                "ultragoal",
                "create-goals",
                "--brief-file",
                str(resolve_command_path(cwd, brief_path_text)),
                "--json",
            )
            return native_argv
        native_argv = ("omx", "ultragoal", "--help")
        return native_argv
    if step.command == CommandStepCommand.OMX_TEAM:
        native_argv = ("omx", "team", "--help")
        return native_argv
    if step.command == CommandStepCommand.OMX_RALPH:
        native_argv = ("omx", "ralph", "--help")
        return native_argv

    native_argv = ("omx", "exec", "--json")
    return native_argv


def native_step_argv(
    cwd: str | Path | None,
    step: CommandStep,
    task_text: str | None,
    runtime_options: CommandRuntimeOptions | None = None,
) -> tuple[str, ...]:
    """Build inspectable native argv for one step.

    Args:
        cwd [str | Path | None]: Base working directory for relative paths.
        step [CommandStep]: Step to render.
        task_text [str | None]: Optional caller-supplied task text.
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        tuple[str, ...]: Native argv preview.
    """
    if step.command == CommandStepCommand.CODEX_EXEC:
        native_argv = _build_codex_argv(
            cwd=cwd,
            step=step,
            task_text=task_text,
            runtime_options=runtime_options,
        )
        return native_argv
    if step.command in {
        CommandStepCommand.OMX_EXEC,
        CommandStepCommand.OMX_ULTRAGOAL,
        CommandStepCommand.OMX_TEAM,
        CommandStepCommand.OMX_RALPH,
    }:
        native_argv = _build_omx_argv(cwd, step)
        return native_argv
    if step.command == CommandStepCommand.LOCAL:
        native_argv = _apply_task_placeholder_to_argv(step.argv, task_text)
        return native_argv
    if step.command == CommandStepCommand.MCP_TOOL:
        server_name: str = "<server>" if step.mcp_server is None else step.mcp_server
        tool_name: str = "<tool>" if step.mcp_tool is None else step.mcp_tool
        native_argv = ("comx-agent", "mcp", "call", server_name, tool_name)
        return native_argv

    native_argv = ("prompt-only",)
    return native_argv
