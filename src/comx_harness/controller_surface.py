from __future__ import annotations

from comx_harness.application.harness_service import HarnessService
from comx_harness.schemas.artifact_schemas import ArtifactReport
from comx_harness.schemas.execution_schemas import (
    ExecutionPlan,
    ExecutionRequest,
    ResumeRequest,
    RunReference,
)
from comx_harness.schemas.handoff_schemas import (
    HandoffExecutionRequest,
    HandoffResult,
)
from comx_harness.schemas.lifecycle_schemas import EventReport, RunRecord, RunState
from comx_harness.schemas.provider_schemas import CapabilityReport


class HarnessTools:
    """Expose the exact public harness operations to trusted controllers."""

    def __init__(self, service: HarnessService | None = None) -> None:
        self.service = service or HarnessService()

    def capabilities(self) -> CapabilityReport:
        """Return installed provider capabilities."""
        report = self.service.capabilities()
        return report

    def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        """Resolve a direct execution plan without launching it."""
        plan = self.service.plan(request)
        return plan

    def run(self, request: ExecutionRequest) -> RunRecord:
        """Execute a direct provider request."""
        record = self.service.run(request)
        return record

    def handoff(self, request: HandoffExecutionRequest) -> HandoffResult:
        """Create one verified cross-runtime handoff."""
        result = self.service.handoff(request.workspace, request)
        return result

    def status(self, request: RunReference) -> RunState:
        """Return semantic state and process liveness for one run."""
        state = self.service.status(request.workspace, request.run_id)
        return state

    def events(self, request: RunReference) -> EventReport:
        """Return normalized events for one run."""
        report = self.service.events(request.workspace, request.run_id)
        return report

    def cancel(self, request: RunReference) -> RunRecord:
        """Request cancellation for one run."""
        record = self.service.cancel(request.workspace, request.run_id)
        return record

    def resume(self, request: ResumeRequest) -> RunRecord:
        """Resume one provider session through its observed identity."""
        record = self.service.resume(
            request.workspace,
            request.run_id,
            request.objective,
            idempotency_key=request.idempotency_key,
        )
        return record

    def artifacts(self, request: RunReference) -> ArtifactReport:
        """Return verified artifacts for one run."""
        report = self.service.artifacts(request.workspace, request.run_id)
        return report
