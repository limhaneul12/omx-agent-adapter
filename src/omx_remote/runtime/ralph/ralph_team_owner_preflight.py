from __future__ import annotations

import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from omx_remote.runtime.ralph.ralph_owner_preflight_settings import (
    RalphOwnerPreflightSettings,
)

COMX_AGENT_OMX_DIST_ROOT_ENV = "COMX_AGENT_OMX_DIST_ROOT"
_OMX_CLI_PATH_PATTERN = re.compile(
    r"""["'](?P<cli_path>[^"']*?/dist/cli/[^"']+\.js)["']"""
)
TEAM_DAG_OWNER_PRESERVATION_FAILURE = (
    "Ralph Team live launch is blocked: installed OMX does not support preserving "
    "Team DAG node.owner assignments, so multi-worker tasks may collapse to worker-1. "
    "Use `comx-agent ralph launch-team --plan-only` to write and inspect the handoff "
    "artifacts, then upgrade OMX to a version that advertises owner-preserving DAG support."
)


def require_ralph_team_live_launch_owner_support(
    omx_dist_root: Path | None = None,
) -> None:
    """Blocks live Ralph Team launch when installed OMX cannot preserve DAG owners.

    Args:
        omx_dist_root [Path | None]: Optional installed OMX distribution root override.

    Raises:
        ValueError: If installed OMX cannot be proven to preserve Team DAG node owners.
    """
    resolved_omx_dist_root, resolution_notes = _resolve_omx_dist_root(omx_dist_root)
    if resolved_omx_dist_root is None:
        raise ValueError(
            _build_ralph_team_owner_preflight_error(
                dist_root=None,
                resolution_notes=resolution_notes,
            )
        )

    owner_preservation_supported, missing_markers = (
        _omx_dist_supports_team_dag_owner_preservation(resolved_omx_dist_root)
    )
    if not owner_preservation_supported:
        raise ValueError(
            _build_ralph_team_owner_preflight_error(
                dist_root=resolved_omx_dist_root,
                resolution_notes=resolution_notes,
                missing_markers=missing_markers,
            )
        )


def _resolve_omx_dist_root(omx_dist_root: Path | None) -> tuple[Path | None, str]:
    """Finds the installed OMX distribution root used for static capability checks.

    Args:
        omx_dist_root [Path | None]: Explicit root supplied by callers or tests.

    Returns:
        tuple[Path | None, str]: Resolved OMX distribution root and an explanation.
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
            f"explicit `omx_dist_root` argument was provided but missing: {omx_dist_root}",
        )

    preflight_settings = RalphOwnerPreflightSettings()
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
        resolved_omx_executable: Path = Path(omx_executable_text)
        dist_root: Path | None = _dist_root_from_omx_executable(resolved_omx_executable)
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
    """Checks whether an installed OMX dist advertises owner-preserving DAG import.

    Args:
        omx_dist_root [Path]: Installed OMX distribution root.

    Returns:
        bool: True when the static contract markers for owner preservation are present.
    """
    team_dir: Path = omx_dist_root / "team"
    dag_schema_type: Path = team_dir / "dag-schema.d.ts"
    dag_schema_runtime: Path = team_dir / "dag-schema.js"
    repo_aware_decomposition: Path = team_dir / "repo-aware-decomposition.js"
    allocation_policy: Path = team_dir / "allocation-policy.js"

    type_contract_marker: str = "owner?: string"
    parser_marker: str = "owner: asOptionalString(node.owner)"
    decomposition_marker: str = "owner: node.owner"
    allocator_marker: str = "preserves explicit DAG owner"

    type_contract_supports_owner: bool = _file_contains(
        dag_schema_type, type_contract_marker
    )
    parser_preserves_owner: bool = _file_contains(dag_schema_runtime, parser_marker)
    decomposition_preserves_owner: bool = _file_contains(
        repo_aware_decomposition, decomposition_marker
    )
    allocator_preserves_owner: bool = _file_contains(
        allocation_policy, allocator_marker
    ) or _file_contains(
        allocation_policy,
        "preserve explicit DAG owner",
    )

    owner_preservation_supported: bool = (
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


def _build_ralph_team_owner_preflight_error(
    dist_root: Path | None,
    resolution_notes: str,
    missing_markers: Sequence[str] = (),
) -> str:
    """Builds a stable user-facing preflight error message for missing owner support.

    Args:
        dist_root [Path | None]: Checked OMX distribution root when resolvable.
        resolution_notes [str]: Human-readable explanation of how the dist root was resolved.
        missing_markers (Sequence[str], default=()): Missing contract markers by file.

    Returns:
        str: Joined error message for user-facing preflight failure text.
    """
    details: list[str] = [TEAM_DAG_OWNER_PRESERVATION_FAILURE]
    details.append(f"Resolution: {resolution_notes}")
    if dist_root is not None:
        details.append(f"Checked OMX dist root: {dist_root}")
    if missing_markers:
        details.append("Unsupported markers:")
        details.extend(missing_markers)
    return " | ".join(details)


def _file_contains(path: Path, marker: str) -> bool:
    """Checks whether a text file contains one static capability marker.

    Args:
        path [Path]: File path to inspect.
        marker [str]: Required marker text.

    Returns:
        bool: True when the file exists and contains the marker.
    """
    if not path.exists():
        missing_marker: bool = False
        return missing_marker

    file_text: str
    try:
        file_text = path.read_text(encoding="utf-8")
    except OSError:
        read_failed: bool = False
        return read_failed
    except UnicodeDecodeError:
        decode_failed: bool = False
        return decode_failed

    contains_marker: bool = marker in file_text
    return contains_marker


def _dist_root_from_omx_executable(omx_executable: Path) -> Path | None:
    """Resolves a dist root candidate from the `omx` executable location.

    Args:
        omx_executable [Path]: Path to the `omx` executable from PATH resolution.

    Returns:
        Path | None: Resolved `.../dist` root, or None when inference fails.
    """
    resolved_executable: Path = _resolve_path(omx_executable)
    direct_dist_root: Path | None = _extract_omx_dist_root_from_path(
        resolved_executable
    )
    if direct_dist_root is not None:
        return direct_dist_root

    launcher_dist_root: Path | None = _extract_omx_dist_root_from_launcher_script(
        resolved_executable
    )
    return launcher_dist_root


def _extract_omx_dist_root_from_path(path: Path) -> Path | None:
    """Infers `dist` root from a `dist/cli/*.js` executable path.

    Args:
        path [Path]: Candidate path that may point at `dist/cli/omx.js`.

    Returns:
        Path | None: Dist root when path pattern matches.
    """
    if path.name != "omx.js" and not path.name.endswith(".js"):
        mismatch: Path | None = None
        return mismatch

    if path.parent.name == "cli" and path.parent.parent.name == "dist":
        extracted_root: Path = path.parent.parent
        return extracted_root

    missing_root: Path | None = None
    return missing_root


def _extract_omx_dist_root_from_launcher_script(launcher_script: Path) -> Path | None:
    """Parses an `omx` launcher script for an embedded `dist/cli/*.js` entrypoint.

    Args:
        launcher_script [Path]: Path to a launcher script that invokes the OMX JS entrypoint.

    Returns:
        Path | None: Inferred `.../dist` root, or None when text marker is absent.
    """
    if not launcher_script.is_file():
        return None

    launch_script_text: str
    try:
        launch_script_text = launcher_script.read_text(encoding="utf-8")
    except OSError:
        unreadable_script: Path | None = None
        return unreadable_script
    except UnicodeDecodeError:
        binary_script: Path | None = None
        return binary_script

    match: re.Match[str] | None = _OMX_CLI_PATH_PATTERN.search(launch_script_text)
    if match is None:
        return None

    cli_path_text: str = match.group("cli_path")
    resolved_cli_path: Path
    if Path(cli_path_text).is_absolute():
        resolved_cli_path = Path(cli_path_text)
    else:
        resolved_cli_path = _resolve_path(launcher_script.parent / cli_path_text)
    return _extract_omx_dist_root_from_path(resolved_cli_path)


def _resolve_path(path: Path) -> Path:
    """Returns `path` even when symlink resolution fails, with fallback semantics.

    Args:
        path [Path]: Input path to normalize.

    Returns:
        Path: resolved path when possible, raw input path otherwise.
    """
    try:
        resolved_path: Path = path.resolve()
    except OSError:
        resolved_path = path
    return resolved_path
