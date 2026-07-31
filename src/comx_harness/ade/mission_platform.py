from __future__ import annotations

from comx_harness.ade.detached_strategies import DetachedStrategyService
from comx_harness.application.mission_observation_service import (
    MissionObservationService,
)
from comx_harness.application.mission_service import MissionService
from comx_harness.schemas.mission_schemas import (
    MissionArtifactReport,
    MissionEventReport,
    MissionPlan,
    MissionRequest,
    MissionStatusReport,
    MissionValidationReport,
)
from comx_harness.schemas.strategy_schemas import StrategyLaunchRecord, StrategyRecord


class AdeMissionTools:
    """Typed Mission surface shared by trusted Agents and human clients."""

    def __init__(
        self,
        service: MissionService | None = None,
        detached: DetachedStrategyService | None = None,
    ) -> None:
        self._service = service or MissionService()
        self._detached = detached or DetachedStrategyService()

    def plan(self, request: MissionRequest) -> MissionPlan:
        return self._service.plan(request)

    def validate(self, request: MissionRequest) -> MissionValidationReport:
        return self._service.validate(request)

    def execute(self, request: MissionRequest) -> StrategyLaunchRecord:
        validation = self._service.validate(request)
        if not validation.valid:
            details = "; ".join(
                issue.detail for issue in validation.strategy_validation.issues
            )
            raise ValueError(f"mission validation failed: {details}")
        self._service.register(request, validation.plan)
        return self._detached.start(validation.plan.strategy)

    def execute_foreground(self, request: MissionRequest) -> StrategyRecord:
        return self._service.execute(request)


class AdeMissionObservationTools:
    """Read-only Mission projection shared by all local clients."""

    def __init__(self, service: MissionObservationService | None = None) -> None:
        self._service = service or MissionObservationService()

    def status(self, workspace: str, mission_id: str) -> MissionStatusReport:
        return self._service.status(workspace, mission_id)

    def events(self, workspace: str, mission_id: str) -> MissionEventReport:
        return self._service.events(workspace, mission_id)

    def artifacts(self, workspace: str, mission_id: str) -> MissionArtifactReport:
        return self._service.artifacts(workspace, mission_id)
