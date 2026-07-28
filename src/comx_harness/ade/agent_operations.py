from __future__ import annotations

from pathlib import Path

from comx_harness.ade.detached_operations import DetachedOperationService
from comx_harness.schemas.ade_agent_schemas import (
    DetachedOperationCollection,
    DetachedOperationReference,
)
from comx_harness.schemas.ade_inspection_schemas import (
    DetachedOperationRecord,
    DetachedOperationRequest,
)
from comx_harness.schemas.ade_schemas import AdeStateSettings
from comx_harness.schemas.execution_schemas import ExecutionRequest, ResumeRequest
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest


class AdeAgentOperations:
    """Typed detached-operation surface shared with the desktop ADE."""

    def __init__(
        self,
        *,
        state_root: str | Path | None = None,
        service: DetachedOperationService | None = None,
    ) -> None:
        settings = (
            AdeStateSettings(state_root=Path(state_root).expanduser().resolve())
            if state_root is not None
            else AdeStateSettings.from_environment()
        )
        self._service = service or DetachedOperationService(settings.state_root)

    def start(self, request: DetachedOperationRequest) -> DetachedOperationRecord:
        if request.operation == "run":
            if not isinstance(request.request, ExecutionRequest):
                raise TypeError("run operation requires ExecutionRequest")
            return self._service.start_run(request.request)
        if request.operation == "resume":
            if not isinstance(request.request, ResumeRequest):
                raise TypeError("resume operation requires ResumeRequest")
            return self._service.start_resume(request.request)
        if not isinstance(request.request, HandoffExecutionRequest):
            raise TypeError("handoff operation requires HandoffExecutionRequest")
        return self._service.start_handoff(request.request)

    def read(self, request: DetachedOperationReference) -> DetachedOperationRecord:
        return self._service.read(request.operation_id)

    def list_records(self) -> DetachedOperationCollection:
        return DetachedOperationCollection(operations=self._service.list_records())
