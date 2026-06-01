from pathlib import Path

from omx_remote.runtime.ralph.ralph_prd import read_ralph_prd_artifact
from omx_remote.schemas.prd_capture_schemas import PrdValidationCaptureResult
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.shared.utils.json_file_store import json_file_stores


def _extract_assignment_worker_ids(
    ralph_prd_artifact: RalphPrdArtifact,
) -> tuple[str, ...]:
    """Extracts declared Team worker IDs from a PRD artifact.

    Args:
        ralph_prd_artifact [RalphPrdArtifact]: Validated PRD artifact.

    Returns:
        tuple[str, ...]: Worker IDs declared in the Team assignment contract.
    """
    if ralph_prd_artifact.team_worker_assignments is None:
        return ()

    worker_ids: list[str] = [
        assignment.worker_id
        for assignment in ralph_prd_artifact.team_worker_assignments
    ]

    return tuple(worker_ids)


def validate_and_capture_prd_artifact(
    input_path: Path,
    output_path: Path | None = None,
) -> PrdValidationCaptureResult:
    """Validate a generated PRD JSON file and optionally capture it for Ralph.

    Args:
        input_path [Path]: Path to a generated PRD JSON artifact.
        output_path [Path | None]: Optional destination, usually `.omx/prd.json`.

    Returns:
        PrdValidationCaptureResult: Summary of the validated/captured PRD.
    """
    ralph_prd_artifact: RalphPrdArtifact = read_ralph_prd_artifact(input_path)

    if output_path is not None:
        json_file_stores.for_path(output_path).write_model(ralph_prd_artifact)

    result = PrdValidationCaptureResult(
        valid=True,
        input_path=str(input_path),
        output_path=None if output_path is None else str(output_path),
        objective=ralph_prd_artifact.objective,
        requires_team_fanout=ralph_prd_artifact.requires_team_fanout,
        team_worker_count=ralph_prd_artifact.team_worker_count,
        assignment_worker_ids=_extract_assignment_worker_ids(ralph_prd_artifact),
    )
    return result
