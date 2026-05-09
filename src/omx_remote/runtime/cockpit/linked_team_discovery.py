from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import orjson
from pydantic import ValidationError

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState

_CODEX_GOAL_MIRROR_STATE_PATH = Path(".agent-remote") / "state" / "codex-goal.json"


@dataclass(frozen=True, slots=True)
class LinkedTeamDiscoveryResult:
    """Represents read-only evidence from cockpit Team-name discovery."""

    discovered_team_names: tuple[str, ...]
    inspected_sources: tuple[str, ...]
    warnings: tuple[str, ...]
    goal_mirror_failure: str | None = None


def discover_linked_team_names(repo_root: str | Path) -> LinkedTeamDiscoveryResult:
    """Discover exact Team names from adapter-owned persisted state when available.

    Args:
        repo_root [str | Path]: Workspace root whose cockpit evidence should be inspected.

    Returns:
        LinkedTeamDiscoveryResult: Discovered names, inspected sources, and warnings.
    """
    goal_mirror_path: Path = _resolve_goal_mirror_state_path(repo_root)
    inspected_sources: tuple[str, ...] = (str(goal_mirror_path),)
    if not goal_mirror_path.exists():
        missing_result = LinkedTeamDiscoveryResult(
            discovered_team_names=(),
            inspected_sources=inspected_sources,
            warnings=(),
        )
        return missing_result

    payload, payload_warning = _read_goal_mirror_payload(goal_mirror_path)
    if payload_warning is not None:
        warning_result = LinkedTeamDiscoveryResult(
            discovered_team_names=(),
            inspected_sources=inspected_sources,
            warnings=(payload_warning,),
            goal_mirror_failure=payload_warning,
        )
        return warning_result

    if payload is None:
        empty_result = LinkedTeamDiscoveryResult(
            discovered_team_names=(),
            inspected_sources=inspected_sources,
            warnings=(),
        )
        return empty_result

    try:
        goal_mirror_state: CodexGoalMirrorState = CodexGoalMirrorState.model_validate(
            payload
        )
    except ValidationError as error:
        validation_warning: str = _format_goal_mirror_validation_warning(
            goal_mirror_path,
            error,
        )
        invalid_result = LinkedTeamDiscoveryResult(
            discovered_team_names=(),
            inspected_sources=inspected_sources,
            warnings=(validation_warning,),
            goal_mirror_failure=validation_warning,
        )
        return invalid_result

    warnings: tuple[str, ...] = _build_goal_mirror_discovery_warnings(
        goal_mirror_path,
        goal_mirror_state,
    )
    result = LinkedTeamDiscoveryResult(
        discovered_team_names=(),
        inspected_sources=inspected_sources,
        warnings=warnings,
    )
    return result


def merge_explicit_and_discovered_team_names(
    explicit_team_names: tuple[str, ...],
    discovered_team_names: tuple[str, ...],
) -> tuple[str, ...]:
    """Merge explicit and discovered Team names while preserving stable order.

    Args:
        explicit_team_names [tuple[str, ...]]: Caller-provided Team names.
        discovered_team_names [tuple[str, ...]]: Read-only discovered Team names.

    Returns:
        tuple[str, ...]: Explicit names first, then new discovered names.
    """
    merged_team_names: list[str] = []
    seen_team_names: set[str] = set()
    for team_name in (*explicit_team_names, *discovered_team_names):
        if team_name in seen_team_names:
            continue

        seen_team_names.add(team_name)
        merged_team_names.append(team_name)

    result: tuple[str, ...] = tuple(merged_team_names)
    return result


def _resolve_goal_mirror_state_path(repo_root: str | Path) -> Path:
    """Resolve the adapter-owned Goal mirror state path for a repo.

    Args:
        repo_root [str | Path]: Workspace root whose mirror state path should be resolved.

    Returns:
        Path: Absolute path to the Goal mirror state file.
    """
    repo_path: Path = Path(repo_root).resolve()
    state_path: Path = repo_path / _CODEX_GOAL_MIRROR_STATE_PATH
    return state_path


def _read_goal_mirror_payload(
    path: Path,
) -> tuple[JsonObject | None, str | None]:
    """Read a Goal mirror JSON object without raising on malformed input.

    Args:
        path [Path]: Goal mirror state path to inspect.

    Returns:
        tuple[JsonObject | None, str | None]: Parsed JSON object and optional warning.
    """
    try:
        raw_payload: bytes = path.read_bytes()
    except OSError as error:
        warning: str = (
            f"Unreadable Goal mirror state at {path}: {_format_os_error(error)}"
        )
        return None, warning

    try:
        parsed_payload: JsonValue = orjson.loads(raw_payload)
    except orjson.JSONDecodeError as error:
        warning = f"Malformed Goal mirror state JSON at {path}: {error}"
        return None, warning

    if not isinstance(parsed_payload, dict):
        warning = f"Malformed Goal mirror state at {path}: expected a JSON object."
        return None, warning

    return parsed_payload, None


def _format_os_error(error: OSError) -> str:
    """Format an OS error for stable warning text.

    Args:
        error [OSError]: Filesystem read error to summarize.

    Returns:
        str: Human-readable error text.
    """
    if error.strerror is not None:
        error_text: str = error.strerror
        return error_text

    error_text = str(error)
    return error_text


def _format_goal_mirror_validation_warning(
    path: Path,
    error: ValidationError,
) -> str:
    """Format a Goal mirror validation failure as cockpit warning text.

    Args:
        path [Path]: Goal mirror state path that failed validation.
        error [ValidationError]: Pydantic validation error from the mirror contract.

    Returns:
        str: Stable warning text for the malformed mirror state.
    """
    error_summary: str = "schema validation failed"
    for error_detail in error.errors():
        message_value: object = error_detail.get("msg")
        if isinstance(message_value, str):
            error_summary = message_value
            break

    warning: str = f"Malformed Goal mirror state at {path}: {error_summary}"
    return warning


def _build_goal_mirror_discovery_warnings(
    path: Path,
    goal_mirror_state: CodexGoalMirrorState,
) -> tuple[str, ...]:
    """Build warnings from valid Goal mirror state that cannot yield exact Team names.

    Args:
        path [Path]: Goal mirror state path that was inspected.
        goal_mirror_state [CodexGoalMirrorState]: Validated Goal mirror state.

    Returns:
        tuple[str, ...]: Warning texts produced from discovery limitations.
    """
    if goal_mirror_state.team_worker_count is None:
        no_warnings: tuple[str, ...] = ()
        return no_warnings

    warning: str = (
        f"Goal mirror state at {path} requests Team fanout with "
        f"{goal_mirror_state.team_worker_count} workers but does not expose exact "
        "Team names."
    )
    warnings: tuple[str, ...] = (warning,)
    return warnings
