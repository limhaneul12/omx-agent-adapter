from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

import orjson

from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandPlanStep,
    CommandStepCommand,
)

_PLACEHOLDER_PATTERN: Final[re.Pattern[str]] = re.compile(r"<([a-zA-Z0-9_-]+)>")


@dataclass
class ExecutionPlaceholderState:
    """Mutable substitution values discovered during execution."""

    run_id: str
    command_id: str
    task_text: str
    route: str = "codex-exec"
    skill_name: str = ""


class CommandPlaceholderKey(StrEnum):
    """Known placeholder keys supported by command execution."""

    TASK = "task"
    ROUTE = "route"
    RUN_ID = "run-id"
    SKILL_NAME = "skill-name"
    PRODUCT_SLUG = "product_slug"
    PRODUCT_SLUG_HYPHEN = "product-slug"
    DATE_TASK_SLUG = "date-task-slug"
    DATED_WORKSPACE = "dated-workspace"
    DESCRIPTIVE_TITLE = "descriptive-title"
    CLOSEOUT_TITLE = "closeout-title"
    SLUG = "slug"


PlaceholderResolver = Callable[[ExecutionPlaceholderState], str]


def safe_generated_name(value: str) -> str:
    """Return a lowercase filesystem/skill safe name.

    Args:
        value: See function signature.

    Returns:
        See function return annotation."""
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    safe_name: str = normalized or "generated-command-artifact"
    return safe_name[:64].strip("-") or "generated-command-artifact"


def _task_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve the task placeholder.

    Args:
        state: See function signature.

    Returns:
        See function return annotation."""
    task_text: str = state.task_text
    return task_text


def _route_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve the route placeholder.

    Args:
        state: See function signature.

    Returns:
        See function return annotation."""
    route: str = state.route
    return route


def _run_id_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve the run id placeholder.

    Args:
        state: See function signature.

    Returns:
        See function return annotation."""
    run_id: str = state.run_id
    return run_id


def _skill_name_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve the generated skill-name placeholder.

    Args:
        state: See function signature.

    Returns:
        See function return annotation."""
    if not state.skill_name:
        state.skill_name = safe_generated_name(f"{state.command_id}-{state.run_id}")
    skill_name: str = state.skill_name
    return skill_name


def _product_slug_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve a stable product slug from the caller task.

    Args:
        state: See function signature.

    Returns:
        See function return annotation."""
    product_slug: str = safe_generated_name(state.task_text)
    return product_slug


def _date_task_slug_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve a dated task workspace folder name.

    Args:
        state: See function signature.

    Returns:
        See function return annotation.
    """
    run_date = state.run_id[:8]
    if len(run_date) == 8 and run_date.isdigit():
        date_text = f"{run_date[:4]}-{run_date[4:6]}-{run_date[6:]}"
    else:
        date_text = safe_generated_name(state.run_id)
    task_slug = safe_generated_name(state.task_text or state.command_id)
    dated_slug = f"{date_text}_{task_slug}"
    return dated_slug


def _generated_artifact_placeholder(state: ExecutionPlaceholderState) -> str:
    """Resolve generic generated artifact placeholders.

    Args:
        state: See function signature.

    Returns:
        See function return annotation."""
    generated_name: str = safe_generated_name(f"{state.command_id}-{state.run_id}")
    return generated_name


PLACEHOLDER_RESOLVERS: Final[dict[CommandPlaceholderKey, PlaceholderResolver]] = {
    CommandPlaceholderKey.TASK: _task_placeholder,
    CommandPlaceholderKey.ROUTE: _route_placeholder,
    CommandPlaceholderKey.RUN_ID: _run_id_placeholder,
    CommandPlaceholderKey.SKILL_NAME: _skill_name_placeholder,
    CommandPlaceholderKey.PRODUCT_SLUG: _product_slug_placeholder,
    CommandPlaceholderKey.PRODUCT_SLUG_HYPHEN: _product_slug_placeholder,
    CommandPlaceholderKey.DATE_TASK_SLUG: _date_task_slug_placeholder,
    CommandPlaceholderKey.DATED_WORKSPACE: _date_task_slug_placeholder,
    CommandPlaceholderKey.DESCRIPTIVE_TITLE: _generated_artifact_placeholder,
    CommandPlaceholderKey.CLOSEOUT_TITLE: _generated_artifact_placeholder,
    CommandPlaceholderKey.SLUG: _generated_artifact_placeholder,
}


def _replacement_for_placeholder(key: str, state: ExecutionPlaceholderState) -> str:
    """Implement replacement for placeholder behavior.

    Args:
        key: See function signature.
        state: See function signature.

    Returns:
        See function return annotation."""
    try:
        placeholder_key = CommandPlaceholderKey(key)
    except ValueError:
        fallback_value: str = safe_generated_name(f"{state.command_id}-{key}")
        return fallback_value

    resolver: PlaceholderResolver = PLACEHOLDER_RESOLVERS[placeholder_key]
    replacement: str = resolver(state)
    return replacement


def replace_placeholders(value: str, state: ExecutionPlaceholderState) -> str:
    """Substitute known recipe placeholders in a string.

    Args:
        value: See function signature.
        state: See function signature.

    Returns:
        See function return annotation."""

    def replace_match(match: re.Match[str]) -> str:
        """Implement replace match behavior.

        Args:
            match: See function signature.

        Returns:
            See function return annotation."""
        replacement = _replacement_for_placeholder(match.group(1), state)
        return replacement

    replaced_value: str = _PLACEHOLDER_PATTERN.sub(replace_match, value)
    return replaced_value


def resolve_artifact_path(path_text: str, state: ExecutionPlaceholderState) -> Path:
    """Resolve an expected artifact path after placeholder substitution.

    Args:
        path_text: See function signature.
        state: See function signature.

    Returns:
        See function return annotation."""
    resolved_text: str = replace_placeholders(path_text, state)
    artifact_path = Path(resolved_text)
    return artifact_path


def _launcher_argv(
    cwd: Path, entrypoint: str, rest: tuple[str, ...]
) -> tuple[str, ...]:
    """Rewrite repo-local agent entrypoints to the current Python launcher when present.

    Args:
        cwd: See function signature.
        entrypoint: See function signature.
        rest: See function signature.

    Returns:
        See function return annotation."""
    launcher_path: Path = cwd / "omx_agent_adapter_cli.py"
    if entrypoint in {"agent-remote", "comx-agent"} and launcher_path.exists():
        argv = (sys.executable, str(launcher_path), *rest)
        return argv
    argv = (entrypoint, *rest)
    return argv


def step_argv(
    step: CommandPlanStep,
    cwd: Path,
    state: ExecutionPlaceholderState,
) -> tuple[str, ...]:
    """Build executable argv for one planned step.

    Args:
        step: See function signature.
        cwd: See function signature.
        state: See function signature.

    Returns:
        See function return annotation."""
    if step.command == CommandStepCommand.MCP_TOOL:
        if step.mcp_server is None or step.mcp_tool is None:
            raise ValueError("mcp_tool steps require both mcp_server and mcp_tool.")
        arguments_json: str = orjson.dumps(step.mcp_arguments).decode()
        base_argv = (
            "comx-agent",
            "mcp",
            "call",
            step.mcp_server,
            step.mcp_tool,
            "--cwd",
            str(cwd),
            "--arguments-json",
            arguments_json,
            "--execute",
            "--json",
        )
    else:
        base_argv = step.native_argv

    substituted: tuple[str, ...] = tuple(
        replace_placeholders(part, state) for part in base_argv
    )
    if not substituted:
        empty_argv: tuple[str, ...] = ()
        return empty_argv
    rewritten = _launcher_argv(cwd, substituted[0], substituted[1:])
    return rewritten


def extract_route_from_stdout(stdout: str, state: ExecutionPlaceholderState) -> None:
    """Update route placeholder state from a route recommendation JSON payload.

    Args:
        stdout: See function signature.
        state: See function signature."""
    try:
        decoded: JsonValue = orjson.loads(stdout)
    except orjson.JSONDecodeError:
        return
    if not isinstance(decoded, dict):
        return
    recommendations = decoded.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        return
    first = recommendations[0]
    if not isinstance(first, dict):
        return
    route = first.get("route")
    if isinstance(route, str) and route:
        state.route = route.replace("_", "-")
