from __future__ import annotations

import re
import sys
from dataclasses import dataclass
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


def safe_generated_name(value: str) -> str:
    """Return a lowercase filesystem/skill safe name.

    Args:
        value: See function signature.

    Returns:
        See function return annotation."""
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    safe_name: str = normalized or "generated-command-artifact"
    return safe_name[:64].strip("-") or "generated-command-artifact"


def _replacement_for_placeholder(key: str, state: ExecutionPlaceholderState) -> str:
    """Implement replacement for placeholder behavior.

    Args:
        key: See function signature.
        state: See function signature.

    Returns:
        See function return annotation."""
    if key == "task":
        return state.task_text
    if key == "route":
        return state.route
    if key == "run-id":
        return state.run_id
    if key == "skill-name":
        if not state.skill_name:
            state.skill_name = safe_generated_name(f"{state.command_id}-{state.run_id}")
        return state.skill_name
    if key in {"descriptive-title", "closeout-title", "slug"}:
        return safe_generated_name(f"{state.command_id}-{state.run_id}")
    return safe_generated_name(f"{state.command_id}-{key}")


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
        arguments_json: str = orjson.dumps(step.mcp_arguments).decode()
        base_argv = (
            "comx-agent",
            "mcp",
            "call",
            step.mcp_server or "",
            step.mcp_tool or "",
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
