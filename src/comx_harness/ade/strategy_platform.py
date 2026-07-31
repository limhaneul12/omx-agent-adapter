from __future__ import annotations

from comx_harness.ade.detached_strategies import DetachedStrategyService
from comx_harness.application.strategy_service import StrategyService
from comx_harness.schemas.capability_matrix_schemas import CapabilityMatrixReport
from comx_harness.schemas.strategy_schemas import (
    StrategyArtifactReport,
    StrategyDefinition,
    StrategyEventReport,
    StrategyLaunchRecord,
    StrategyRecord,
    StrategyValidationReport,
)


class AdeStrategyTools:
    """Typed Agent surface for Strategy validation and execution."""

    def __init__(
        self,
        service: StrategyService | None = None,
        detached: DetachedStrategyService | None = None,
    ) -> None:
        self._service = service or StrategyService()
        self._detached = detached or DetachedStrategyService()

    def capabilities(self) -> CapabilityMatrixReport:
        return self._service.capabilities()

    def validate(self, definition: StrategyDefinition) -> StrategyValidationReport:
        return self._service.validate(definition)

    def execute(self, definition: StrategyDefinition) -> StrategyLaunchRecord:
        return self._detached.start(definition)

    def execute_foreground(self, definition: StrategyDefinition) -> StrategyRecord:
        return self._service.execute(definition)


class AdeStrategyObservationTools:
    """Typed Agent surface for reading durable Strategy state."""

    def __init__(
        self,
        service: StrategyService | None = None,
        detached: DetachedStrategyService | None = None,
    ) -> None:
        self._service = service or StrategyService()
        self._detached = detached or DetachedStrategyService()

    def launch_status(self, workspace: str, strategy_id: str) -> StrategyLaunchRecord:
        return self._detached.read(workspace, strategy_id)

    def status(self, workspace: str, strategy_id: str) -> StrategyRecord:
        return self._service.status(workspace, strategy_id)

    def events(self, workspace: str, strategy_id: str) -> StrategyEventReport:
        return self._service.events(workspace, strategy_id)

    def artifacts(self, workspace: str, strategy_id: str) -> StrategyArtifactReport:
        return self._service.artifacts(workspace, strategy_id)
