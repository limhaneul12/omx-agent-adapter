from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from comx_harness.ade.detached_operations import DetachedOperationService
from comx_harness.ade.omx_team_native import OmxTeamObserver
from comx_harness.ade.recipe_catalog import build_recipe_request, recipe_by_id
from comx_harness.ade.run_projection import WorkspaceRunProjectionReader
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.ade_inspection_schemas import DetachedOperationRecord
from comx_harness.schemas.ade_operator_schemas import (
    RunInspection,
    WorkspaceRunProjection,
)
from comx_harness.schemas.execution_schemas import (
    ExecutionPlan,
    ExecutionRequest,
    ResumeRequest,
    RunOptions,
    RunReference,
)
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.schemas.omx_team_schemas import OmxTeamProjection
from comx_harness.schemas.provider_schemas import CapabilityReport
from comx_harness.shared.harness_enums.execution_enums import SandboxMode
from comx_harness.shared.harness_enums.operator_enums import RecipeId
from comx_harness.shared.harness_enums.provider_enums import ProviderId


class AdeLaunchController:
    """Preview and start one exact, idempotent Run from the desktop ADE."""

    def __init__(
        self,
        workspace: Path,
        tools: HarnessTools,
        detached: DetachedOperationService,
    ) -> None:
        self._workspace = workspace
        self._tools = tools
        self._detached = detached
        self._request: ExecutionRequest | None = None
        self._plan: ExecutionPlan | None = None

    def plan(self, recipe_id: RecipeId | str, objective: str) -> ExecutionPlan:
        request = build_recipe_request(
            recipe=recipe_by_id(recipe_id),
            objective=objective,
            workspace=self._workspace,
            controller_id="human-ade",
        ).model_copy(update={"idempotency_key": f"ade-{uuid4().hex}"})
        plan = self._tools.plan(request)
        self._request = request
        self._plan = plan
        return plan

    def planned_execution(self) -> ExecutionPlan | None:
        return self._plan

    def clear_plan(self) -> None:
        self._request = None
        self._plan = None

    def start_planned(self) -> DetachedOperationRecord:
        request = self._request
        if request is None or self._plan is None:
            raise ValueError("review a plan before starting the Run")
        operation = self._detached.start_run(request)
        self.clear_plan()
        return operation


class AdeObservationController:
    """Project core lifecycle evidence into ADE workspace and Run views."""

    def __init__(
        self,
        workspace: Path,
        tools: HarnessTools,
        projection_reader: WorkspaceRunProjectionReader,
        team_observer: OmxTeamObserver,
    ) -> None:
        self._workspace = workspace
        self._tools = tools
        self._projection_reader = projection_reader
        self._team_observer = team_observer

    def capabilities(self) -> CapabilityReport:
        return self._tools.capabilities()

    def projection(self) -> WorkspaceRunProjection:
        return self._projection_reader.read(self._workspace)

    def inspect(self, run_id: str) -> RunInspection:
        reference = RunReference(workspace=str(self._workspace), run_id=run_id)
        events = self._tools.events(reference)
        return RunInspection(
            state=self._tools.status(reference),
            events=events,
            artifacts=self._tools.artifacts(reference),
            discovered_omx_teams=self._team_observer.discover(events),
        )

    def team(self, team_name: str) -> OmxTeamProjection:
        return self._team_observer.read(team_name)


class AdeControlController:
    """Expose bounded lifecycle controls without taking provider ownership."""

    def __init__(
        self,
        workspace: Path,
        tools: HarnessTools,
        detached: DetachedOperationService,
    ) -> None:
        self._workspace = workspace
        self._tools = tools
        self._detached = detached

    def cancel(self, run_id: str) -> RunRecord:
        return self._tools.cancel(
            RunReference(workspace=str(self._workspace), run_id=run_id)
        )

    def resume(
        self,
        run_id: str,
        objective: str | None = None,
    ) -> DetachedOperationRecord:
        return self._detached.start_resume(
            ResumeRequest(
                workspace=str(self._workspace),
                run_id=run_id,
                objective=objective,
                idempotency_key=f"ade-resume-{uuid4().hex}",
            )
        )

    def handoff(
        self,
        run_id: str,
        objective: str,
    ) -> DetachedOperationRecord:
        reference = RunReference(workspace=str(self._workspace), run_id=run_id)
        state = self._tools.status(reference)
        target = (
            ProviderId.OMX
            if state.record.provider == ProviderId.CODEX
            else ProviderId.CODEX
        )
        request = HandoffExecutionRequest(
            workspace=str(self._workspace),
            controller_id="human-ade",
            origin_run_id=run_id,
            target_provider=target,
            objective=objective,
            mutation_allowed=False,
            idempotency_key=f"ade-handoff-{uuid4().hex}",
            options=RunOptions(sandbox=SandboxMode.READ_ONLY),
        )
        return self._detached.start_handoff(request)


class AdeController:
    """Composition root for one selected ADE Workspace."""

    def __init__(
        self,
        workspace: str | Path,
        state_root: str | Path,
        *,
        tools: HarnessTools | None = None,
    ) -> None:
        resolved_workspace = Path(workspace).expanduser().resolve()
        shared_tools = tools or HarnessTools()
        detached = DetachedOperationService(state_root)
        team_observer = OmxTeamObserver(resolved_workspace)
        self.workspace = resolved_workspace
        self.launch = AdeLaunchController(
            resolved_workspace,
            shared_tools,
            detached,
        )
        self.observe = AdeObservationController(
            resolved_workspace,
            shared_tools,
            WorkspaceRunProjectionReader(
                shared_tools,
                team_observer=team_observer,
            ),
            team_observer,
        )
        self.control = AdeControlController(
            resolved_workspace,
            shared_tools,
            detached,
        )
