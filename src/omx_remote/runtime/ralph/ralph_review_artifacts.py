from pathlib import Path

import orjson

from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.ralph.review_schemas import RalphPostTeamReviewResult
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReport,
)


def read_ralph_prd_artifact_file(prd_path: Path) -> RalphPrdArtifact:
    """Reads a strict Ralph PRD artifact from a JSON file.

    Args:
        prd_path [Path]: JSON file containing a RalphPrdArtifact payload.

    Returns:
        RalphPrdArtifact: Validated Ralph PRD artifact from the file.
    """
    prd_payload = orjson.loads(prd_path.read_bytes())
    prd_artifact: RalphPrdArtifact = RalphPrdArtifact.model_validate(prd_payload)
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
    report_payload = orjson.loads(report_path.read_bytes())
    report: TeamAdminAggregationReport = TeamAdminAggregationReport.model_validate(
        report_payload
    )
    return report


def read_ralph_post_team_review_artifact(review_path: Path) -> RalphPostTeamReviewResult:
    """Reads a strict Ralph post-Team review result from a JSON file.

    Args:
        review_path [Path]: JSON file containing a RalphPostTeamReviewResult payload.

    Returns:
        RalphPostTeamReviewResult: Validated Ralph post-Team review result from the file.
    """
    review_payload = orjson.loads(review_path.read_bytes())
    review_result: RalphPostTeamReviewResult = RalphPostTeamReviewResult.model_validate(
        review_payload
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload: bytes = orjson.dumps(
        review_result.model_dump(mode="json"),
        option=orjson.OPT_INDENT_2,
    )
    output_path.write_bytes(output_payload)
    written_path: Path = output_path
    return written_path
