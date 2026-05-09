from __future__ import annotations

import os
from pathlib import Path

AGENT_REMOTE_OMX_DIST_ROOT_ENV = "AGENT_REMOTE_OMX_DIST_ROOT"
TEAM_DAG_OWNER_PRESERVATION_FAILURE = (
    "Ralph Team live launch is blocked: installed OMX does not support preserving "
    "Team DAG node.owner assignments, so multi-worker tasks may collapse to worker-1. "
    "Use `agent-remote ralph launch-team --plan-only` to write and inspect the handoff "
    "artifacts, then upgrade OMX to a version that advertises owner-preserving DAG support."
)

_KNOWN_OMX_DIST_ROOTS: tuple[Path, ...] = (
    Path("/opt/homebrew/lib/node_modules/oh-my-codex/dist"),
    Path("/usr/local/lib/node_modules/oh-my-codex/dist"),
)


def require_ralph_team_live_launch_owner_support(omx_dist_root: Path | None = None) -> None:
    """Blocks live Ralph Team launch when installed OMX cannot preserve DAG owners.

    Args:
        omx_dist_root [Path | None]: Optional installed OMX distribution root override.

    Raises:
        ValueError: If installed OMX cannot be proven to preserve Team DAG node owners.
    """
    resolved_omx_dist_root: Path | None = _resolve_omx_dist_root(omx_dist_root)
    if resolved_omx_dist_root is None:
        raise ValueError(TEAM_DAG_OWNER_PRESERVATION_FAILURE)

    owner_preservation_supported: bool = _omx_dist_supports_team_dag_owner_preservation(
        resolved_omx_dist_root
    )
    if not owner_preservation_supported:
        raise ValueError(TEAM_DAG_OWNER_PRESERVATION_FAILURE)


def _resolve_omx_dist_root(omx_dist_root: Path | None) -> Path | None:
    """Finds the installed OMX distribution root used for static capability checks.

    Args:
        omx_dist_root [Path | None]: Explicit root supplied by callers or tests.

    Returns:
        Path | None: Existing OMX distribution root, or None when unavailable.
    """
    if omx_dist_root is not None:
        if omx_dist_root.exists():
            explicit_root: Path | None = omx_dist_root
            return explicit_root
        missing_explicit_root: Path | None = None
        return missing_explicit_root

    env_root_text: str | None = os.environ.get(AGENT_REMOTE_OMX_DIST_ROOT_ENV)
    if env_root_text is not None:
        env_root = Path(env_root_text)
        if env_root.exists():
            resolved_env_root: Path | None = env_root
            return resolved_env_root
        missing_env_root: Path | None = None
        return missing_env_root

    for known_root in _KNOWN_OMX_DIST_ROOTS:
        if known_root.exists():
            resolved_known_root: Path | None = known_root
            return resolved_known_root

    missing_root: Path | None = None
    return missing_root


def _omx_dist_supports_team_dag_owner_preservation(omx_dist_root: Path) -> bool:
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

    type_contract_supports_owner: bool = _file_contains(dag_schema_type, "owner?: string")
    parser_preserves_owner: bool = _file_contains(dag_schema_runtime, "owner: asOptionalString(node.owner)")
    decomposition_preserves_owner: bool = _file_contains(repo_aware_decomposition, "owner: node.owner")
    allocator_preserves_owner: bool = _file_contains(
        allocation_policy,
        "preserves explicit DAG owner",
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
    return owner_preservation_supported


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
