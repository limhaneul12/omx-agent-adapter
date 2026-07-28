from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from comx_harness.ade.controller import AdeController
from comx_harness.ade.diff_service import GitDiffService
from comx_harness.schemas.ade_inspection_schemas import GitDiffProjection
from comx_harness.schemas.ade_operator_schemas import RunInspection
from comx_harness.schemas.omx_team_schemas import OmxTeamProjection


@dataclass(frozen=True, slots=True)
class RunInspectionSnapshot:
    workspace: Path
    run_id: str
    inspection: RunInspection
    diff: GitDiffProjection
    team: OmxTeamProjection | None


class RunInspectionReader:
    """Collect Run detail evidence without touching Tk widgets."""

    def __init__(self, diff: GitDiffService) -> None:
        self._diff = diff

    def read(
        self,
        controller: AdeController,
        run_id: str,
    ) -> RunInspectionSnapshot:
        inspection = controller.observe.inspect(run_id)
        diff = self._diff.inspect(controller.workspace)
        team = (
            controller.observe.team(inspection.discovered_omx_teams[0])
            if inspection.discovered_omx_teams
            else None
        )
        snapshot = RunInspectionSnapshot(
            workspace=controller.workspace,
            run_id=run_id,
            inspection=inspection,
            diff=diff,
            team=team,
        )
        return snapshot
