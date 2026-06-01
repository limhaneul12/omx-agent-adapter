from pathlib import Path

import orjson
from pydantic import BaseModel

from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
)
from omx_remote.shared.utils.json_file_store import json_file_stores


def _read_json_model_artifact[ModelT: BaseModel](
    path: Path,
    model_type: type[ModelT],
) -> ModelT:
    """Read one JSON artifact and validate it as a Pydantic model.

    Args:
        path [Path]: JSON artifact path to read.
        model_type [type[ModelT]]: Pydantic model class used for validation.

    Returns:
        ModelT: Validated model instance.
    """
    artifact_payload = orjson.loads(path.read_bytes())
    artifact_model: ModelT = model_type.model_validate(artifact_payload)
    return artifact_model


def read_ralph_prd_artifact_file(prd_path: Path) -> RalphPrdArtifact:
    """Reads a strict Ralph PRD artifact from a JSON file.

    Args:
        prd_path [Path]: JSON file containing a RalphPrdArtifact payload.

    Returns:
        RalphPrdArtifact: Validated Ralph PRD artifact from the file.
    """
    prd_artifact = _read_json_model_artifact(prd_path, RalphPrdArtifact)
    return prd_artifact


def read_team_admin_aggregation_report_artifact(
    report_path: Path,
) -> TeamAdminAggregationReport:
    """Reads a strict Team Admin aggregation report from a JSON file.

    Args:
        report_path [Path]: JSON file containing a TeamAdminAggregationReport payload.

    Returns:
        TeamAdminAggregationReport: Validated Team Admin aggregation report from the file.
    """
    report = _read_json_model_artifact(
        report_path,
        TeamAdminAggregationReport,
    )
    return report


def read_ralph_post_team_review_artifact(
    review_path: Path,
) -> RalphPostTeamReviewResult:
    """Reads a strict Ralph post-Team review result from a JSON file.

    Args:
        review_path [Path]: JSON file containing a RalphPostTeamReviewResult payload.

    Returns:
        RalphPostTeamReviewResult: Validated Ralph post-Team review result from the file.
    """
    review_result = _read_json_model_artifact(
        review_path,
        RalphPostTeamReviewResult,
    )
    return review_result


def write_ralph_post_team_review_artifact(
    review_result: RalphPostTeamReviewResult,
    output_path: Path,
) -> Path:
    """Writes one Ralph post-Team review result artifact as indented JSON.

    Args:
        review_result [RalphPostTeamReviewResult]: Review result to persist.
        output_path [Path]: JSON destination path.

    Returns:
        Path: Path written by the artifact writer.
    """
    json_file_stores.for_path(output_path).write_model(review_result)
    written_path: Path = output_path
    return written_path
