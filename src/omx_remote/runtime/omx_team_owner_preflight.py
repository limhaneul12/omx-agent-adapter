from __future__ import annotations

import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from omx_remote.runtime.omx_team_owner_preflight_settings import (
    OmxTeamOwnerPreflightSettings,
)

COMX_AGENT_OMX_DIST_ROOT_ENV = "COMX_AGENT_OMX_DIST_ROOT"
_OMX_CLI_PATH_PATTERN = re.compile(
    r"""["'](?P<cli_path>[^"']*?/dist/cli/[^"']+\.js)["']"""
)


def owner_preservation_failure_message(launch_context: str) -> str:
    """Build the base owner-preservation failure message.

    Args:
        launch_context [str]: Human-readable Team launch context.

    Returns:
        str: User-facing failure message prefix.
    """
    message = (
        f"{launch_context} is blocked: installed OMX does not support preserving "
        "Team DAG node.owner assignments, so multi-worker tasks may collapse to "
        "worker-1. Write and inspect handoff artifacts, then upgrade OMX to a "
        "version that advertises owner-preserving DAG support before live fanout."
    )
    return message


def require_omx_team_live_launch_owner_support(
    omx_dist_root: Path | None = None,
    launch_context: str = "OMX Team live launch",
) -> None:
    """Block live Team launch when installed OMX cannot preserve DAG owners.

    Args:
        omx_dist_root [Path | None]: Optional installed OMX distribution root override.
        launch_context [str]: Human-readable context for the launch being guarded.

    Raises:
        ValueError: If installed OMX cannot be proven to preserve Team DAG node owners.
    """
    resolved_omx_dist_root, resolution_notes = _resolve_omx_dist_root(omx_dist_root)
    if resolved_omx_dist_root is None:
        raise ValueError(
            _build_omx_team_owner_preflight_error(
                launch_context=launch_context,
                dist_root=None,
                resolution_notes=resolution_notes,
            )
        )

    owner_preservation_supported, missing_markers = (
        _omx_dist_supports_team_dag_owner_preservation(resolved_omx_dist_root)
    )
    if not owner_preservation_supported:
        raise ValueError(
            _build_omx_team_owner_preflight_error(
                launch_context=launch_context,
                dist_root=resolved_omx_dist_root,
                resolution_notes=resolution_notes,
                missing_markers=missing_markers,
            )
        )


def _resolve_omx_dist_root(omx_dist_root: Path | None) -> tuple[Path | None, str]:
    """Find the installed OMX distribution root used for static checks.

    Args:
        omx_dist_root [Path | None]: Explicit root supplied by callers or tests.

    Returns:
        tuple[Path | None, str]: Resolved OMX distribution root and explanation.
    """
    if omx_dist_root is not None:
        if omx_dist_root.exists():
            explicit_root: Path | None = omx_dist_root
            return (
                explicit_root,
                f"resolved from explicit `omx_dist_root` argument: {explicit_root}",
            )
        missing_explicit_root: Path | None = None
        return (
            missing_explicit_root,
            "explicit `omx_dist_root` argument was provided but missing: "
            f"{omx_dist_root}",
        )

    preflight_settings = OmxTeamOwnerPreflightSettings()
    env_root: Path | None = preflight_settings.omx_dist_root
    if env_root is not None:
        if env_root.exists():
            resolved_env_root: Path | None = env_root
            return (
                resolved_env_root,
                f"resolved from {COMX_AGENT_OMX_DIST_ROOT_ENV}={resolved_env_root}",
            )
        missing_env_root: Path | None = None
        return (
            missing_env_root,
            f"{COMX_AGENT_OMX_DIST_ROOT_ENV} was set but path did not exist: {env_root}",
        )

    omx_executable_text = shutil.which("omx")
    if omx_executable_text is not None:
        resolved_omx_executable = Path(omx_executable_text)
        dist_root: Path | None = _dist_root_from_omx_executable(
            resolved_omx_executable
        )
        if dist_root is not None and dist_root.exists():
            return (
                dist_root,
                f"resolved from PATH `omx` executable `{resolved_omx_executable}`",
            )
        return None, (
            "PATH `omx` executable exists but could not be mapped to a dist/cli root: "
            f"{resolved_omx_executable}"
        )

    return (
        None,
        "could not resolve OMX dist root from explicit override, env var, or PATH",
    )


def _omx_dist_supports_team_dag_owner_preservation(
    omx_dist_root: Path,
) -> tuple[bool, list[str]]:
    """Check whether installed OMX advertises owner-preserving DAG import.

    Args:
        omx_dist_root [Path]: Installed OMX distribution root.

    Returns:
        tuple[bool, list[str]]: Support flag and missing marker descriptions.
    """
    team_dir = omx_dist_root / "team"
    dag_schema_type = team_dir / "dag-schema.d.ts"
    dag_schema_runtime = team_dir / "dag-schema.js"
    repo_aware_decomposition = team_dir / "repo-aware-decomposition.js"
    allocation_policy = team_dir / "allocation-policy.js"

    type_contract_marker = "owner?: string"
    parser_marker = "owner: asOptionalString(node.owner)"
    decomposition_marker = "owner: node.owner"
    allocator_marker = "preserves explicit DAG owner"

    type_contract_supports_owner = _file_contains(dag_schema_type, type_contract_marker)
    parser_preserves_owner = _file_contains(dag_schema_runtime, parser_marker)
    decomposition_preserves_owner = _file_contains(
        repo_aware_decomposition,
        decomposition_marker,
    )
    allocator_preserves_owner = _file_contains(
        allocation_policy,
        allocator_marker,
    ) or _file_contains(
        allocation_policy,
        "preserve explicit DAG owner",
    )

    owner_preservation_supported = (
        type_contract_supports_owner
        and parser_preserves_owner
        and decomposition_preserves_owner
        and allocator_preserves_owner
    )
    missing_markers: list[str] = []
    if not type_contract_supports_owner:
        missing_markers.append(
            f"missing marker in `team/dag-schema.d.ts`: {type_contract_marker}"
        )
    if not parser_preserves_owner:
        missing_markers.append(
            f"missing marker in `team/dag-schema.js`: {parser_marker}"
        )
    if not decomposition_preserves_owner:
        missing_markers.append(
            "missing marker in `team/repo-aware-decomposition.js`: owner: node.owner"
        )
    if not allocator_preserves_owner:
        missing_markers.append(
            "missing marker in `team/allocation-policy.js`: preserves explicit DAG owner"
        )

    return owner_preservation_supported, missing_markers


def _build_omx_team_owner_preflight_error(
    launch_context: str,
    dist_root: Path | None,
    resolution_notes: str,
    missing_markers: Sequence[str] = (),
) -> str:
    """Build a stable user-facing preflight error message.

    Args:
        launch_context [str]: Human-readable Team launch context.
        dist_root [Path | None]: Checked OMX distribution root when resolvable.
        resolution_notes [str]: Human-readable explanation of dist-root resolution.
        missing_markers [Sequence[str]]: Missing contract markers by file.

    Returns:
        str: Joined error message for user-facing preflight failure text.
    """
    details: list[str] = [owner_preservation_failure_message(launch_context)]
    details.append(f"Resolution: {resolution_notes}")
    if dist_root is not None:
        details.append(f"Checked OMX dist root: {dist_root}")
    if missing_markers:
        details.append("Unsupported markers:")
        details.extend(missing_markers)
    return " | ".join(details)


def _file_contains(path: Path, marker: str) -> bool:
    """Check whether a text file contains one static capability marker.

    Args:
        path [Path]: File path to inspect.
        marker [str]: Required marker text.

    Returns:
        bool: True when the file exists and contains the marker.
    """
    if not path.exists():
        missing_marker = False
        return missing_marker

    file_text: str
    try:
        file_text = path.read_text(encoding="utf-8")
    except OSError:
        read_failed = False
        return read_failed
    except UnicodeDecodeError:
        decode_failed = False
        return decode_failed

    contains_marker = marker in file_text
    return contains_marker


def _dist_root_from_omx_executable(omx_executable: Path) -> Path | None:
    """Resolve a dist root candidate from the `omx` executable location.

    Args:
        omx_executable [Path]: Path to the `omx` executable from PATH resolution.

    Returns:
        Path | None: Resolved `.../dist` root, or None when inference fails.
    """
    resolved_executable = _resolve_path(omx_executable)
    direct_dist_root = _extract_omx_dist_root_from_path(resolved_executable)
    if direct_dist_root is not None:
        return direct_dist_root

    launcher_dist_root = _extract_omx_dist_root_from_launcher_script(
        resolved_executable
    )
    return launcher_dist_root


def _extract_omx_dist_root_from_path(path: Path) -> Path | None:
    """Infer `dist` root from a `dist/cli/*.js` executable path.

    Args:
        path [Path]: Candidate path that may point at `dist/cli/omx.js`.

    Returns:
        Path | None: Dist root when path pattern matches.
    """
    path_parts = path.parts
    if "dist" not in path_parts or "cli" not in path_parts:
        return None
    dist_index = path_parts.index("dist")
    if dist_index + 1 >= len(path_parts) or path_parts[dist_index + 1] != "cli":
        return None
    dist_root = Path(*path_parts[: dist_index + 1])
    return dist_root


def _extract_omx_dist_root_from_launcher_script(launcher_path: Path) -> Path | None:
    """Infer `dist` root from an executable launcher script.

    Args:
        launcher_path [Path]: Candidate launcher path to inspect.

    Returns:
        Path | None: Dist root when script text references a dist/cli entrypoint.
    """
    try:
        launcher_text = launcher_path.read_text(encoding="utf-8")
    except OSError:
        missing_root: Path | None = None
        return missing_root
    except UnicodeDecodeError:
        missing_root = None
        return missing_root

    match = _OMX_CLI_PATH_PATTERN.search(launcher_text)
    if match is None:
        missing_root = None
        return missing_root
    cli_path = Path(match.group("cli_path"))
    dist_root = _extract_omx_dist_root_from_path(cli_path)
    return dist_root


def _resolve_path(path: Path) -> Path:
    """Resolve symlinks without failing on missing launcher targets.

    Args:
        path [Path]: Path to resolve.

    Returns:
        Path: Best-effort resolved path.
    """
    try:
        resolved_path = path.resolve(strict=False)
    except OSError:
        resolved_path = path
    return resolved_path
