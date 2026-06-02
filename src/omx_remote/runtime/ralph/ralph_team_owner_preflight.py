from pathlib import Path

from omx_remote.runtime.omx_team_owner_preflight import (
    owner_preservation_failure_message,
    require_omx_team_live_launch_owner_support,
)

TEAM_DAG_OWNER_PRESERVATION_FAILURE = owner_preservation_failure_message(
    "Ralph Team live launch"
)


def require_ralph_team_live_launch_owner_support(
    omx_dist_root: Path | None = None,
) -> None:
    """Block live Ralph Team launch when installed OMX cannot preserve DAG owners.

    Args:
        omx_dist_root [Path | None]: Optional installed OMX distribution root override.

    Raises:
        ValueError: If installed OMX cannot be proven to preserve Team DAG node owners.
    """
    require_omx_team_live_launch_owner_support(
        omx_dist_root=omx_dist_root,
        launch_context="Ralph Team live launch",
    )
