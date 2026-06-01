import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError

from omx_remote.runtime.ralph.ralph_review_artifacts import read_ralph_prd_artifact_file
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact
from omx_remote.schemas.teamwork.admin_aggregation_schemas import (
    TeamAdminAggregationReportRequest,
)
from omx_remote.teamwork.team_admin_aggregation import (
    read_team_admin_aggregation_report,
    write_team_admin_aggregation_report_artifact,
)


def register_team_admin_commands(team_app: typer.Typer) -> None:
    """Register Team Admin aggregation commands.

    Args:
        team_app [typer.Typer]: Typer app receiving Team Admin commands.
    """

    @team_app.command("admin-report")
    def team_admin_report(
        team: str = typer.Option(..., "--team", help="Team name to aggregate."),
        prd_path: Path = typer.Option(
            ...,
            "--prd-path",
            help="Path to the RalphPrdArtifact JSON file.",
        ),
        output_path: Path | None = typer.Option(
            None,
            "--output-path",
            help="Optional path where the aggregation report JSON should be written.",
        ),
    ) -> None:
        """Read Team evidence and emit one Team Admin aggregation report.

        Args:
            team [str]: Team name to aggregate.
            prd_path [Path]: Path to the Ralph PRD artifact JSON file.
            output_path [Path | None]: Optional JSON artifact destination.
        """
        try:
            prd_artifact: RalphPrdArtifact = read_ralph_prd_artifact_file(prd_path)
            request: TeamAdminAggregationReportRequest = (
                TeamAdminAggregationReportRequest(
                    team_name=team,
                    ralph_prd_artifact=prd_artifact,
                )
            )
            report = asyncio.run(read_team_admin_aggregation_report(request))
            if output_path is not None:
                write_team_admin_aggregation_report_artifact(report, output_path)
        except (OSError, ValidationError, ValueError) as error:
            typer.echo(str(error))
            raise typer.Exit(code=2) from error

        typer.echo(report.model_dump_json(indent=2))
