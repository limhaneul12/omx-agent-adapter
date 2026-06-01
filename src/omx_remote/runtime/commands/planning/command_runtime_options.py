import shlex
from typing import Final

from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.shared.omx_enums.agent_enums import AgentEffort

_CODEX_REASONING_CONFIG_KEY: Final[str] = "model_reasoning_effort"
_CODEX_MADMAX_FLAG: Final[str] = "--dangerously-bypass-approvals-and-sandbox"
_OMX_TEAM_WORKER_LAUNCH_ARGS: Final[str] = "OMX_TEAM_WORKER_LAUNCH_ARGS"


def _parse_reasoning_effort(reasoning_effort: str | None) -> AgentEffort | None:
    """Parse a CLI reasoning effort value into the shared effort enum.

    Args:
        reasoning_effort [str | None]: Caller-supplied effort text.

    Returns:
        AgentEffort | None: Parsed effort when supplied.
    """
    if reasoning_effort is None:
        missing_effort: None = None
        return missing_effort
    try:
        effort = AgentEffort(reasoning_effort.lower())
    except ValueError as error:
        allowed_values = ", ".join(effort.value for effort in AgentEffort)
        raise ValueError(
            f"--reasoning-effort must be one of: {allowed_values}"
        ) from error
    return effort


def build_command_runtime_options(
    model: str | None,
    reasoning_effort: str | None,
    xhigh: bool,
    madmax: bool,
) -> CommandRuntimeOptions | None:
    """Build typed runtime options from CLI/TUI inputs.

    Args:
        model [str | None]: Explicit Codex model.
        reasoning_effort [str | None]: Explicit reasoning effort.
        xhigh [bool]: Shortcut for `--reasoning-effort xhigh`.
        madmax [bool]: Dangerous shortcut for xhigh plus sandbox/approval bypass.

    Returns:
        CommandRuntimeOptions | None: Typed options when at least one override exists.
    """
    parsed_effort = _parse_reasoning_effort(reasoning_effort=reasoning_effort)
    shortcut_effort = AgentEffort.XHIGH if xhigh or madmax else None
    if (
        parsed_effort is not None
        and shortcut_effort is not None
        and parsed_effort != shortcut_effort
    ):
        raise ValueError(
            "--xhigh/--madmax cannot be combined with a different --reasoning-effort"
        )
    effective_effort = parsed_effort or shortcut_effort
    if model is None and effective_effort is None and not madmax:
        no_options: None = None
        return no_options
    options = CommandRuntimeOptions(
        model=model,
        reasoning_effort=effective_effort,
        madmax=madmax,
    )
    return options


def codex_runtime_argv(
    runtime_options: CommandRuntimeOptions | None,
) -> tuple[str, ...]:
    """Return Codex CLI argv fragments for runtime options.

    Args:
        runtime_options [CommandRuntimeOptions | None]: Optional runtime controls.

    Returns:
        tuple[str, ...]: Codex argv fragment.
    """
    if runtime_options is None:
        empty_args: tuple[str, ...] = ()
        return empty_args
    args: list[str] = []
    if runtime_options.model is not None:
        args.extend(["--model", runtime_options.model])
    if runtime_options.reasoning_effort is not None:
        args.extend(
            [
                "-c",
                f'{_CODEX_REASONING_CONFIG_KEY}="{runtime_options.reasoning_effort}"',
            ]
        )
    if runtime_options.madmax:
        args.append(_CODEX_MADMAX_FLAG)
    return tuple(args)


def team_worker_launch_args(
    runtime_options: CommandRuntimeOptions | None,
) -> str | None:
    """Render transient OMX Team worker launch args from runtime options.

    Args:
        runtime_options [CommandRuntimeOptions | None]: Optional runtime controls.

    Returns:
        str | None: Worker launch args string when options should affect Team workers.
    """
    args = codex_runtime_argv(runtime_options=runtime_options)
    if not args:
        no_launch_args: None = None
        return no_launch_args
    launch_args = shlex.join(args)
    return launch_args


def team_worker_launch_environment_name() -> str:
    """Return the OMX worker launch-args environment key used at subprocess time.

    Returns:
        str: Environment key.
    """
    return _OMX_TEAM_WORKER_LAUNCH_ARGS


def runtime_options_summary_text(
    runtime_options: CommandRuntimeOptions | None,
) -> str:
    """Render runtime options for human-facing artifacts.

    Args:
        runtime_options [CommandRuntimeOptions | None]: Optional runtime controls.

    Returns:
        str: Human-readable runtime option summary.
    """
    if runtime_options is None:
        return "default model and reasoning from Codex/OMX configuration"
    parts: list[str] = []
    if runtime_options.model is not None:
        parts.append(f"model={runtime_options.model}")
    if runtime_options.reasoning_effort is not None:
        parts.append(f"reasoning_effort={runtime_options.reasoning_effort}")
    if runtime_options.madmax:
        parts.append("madmax=true")
    summary = ", ".join(parts)
    return summary
