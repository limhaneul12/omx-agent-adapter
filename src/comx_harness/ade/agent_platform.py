from __future__ import annotations

from pathlib import Path

from comx_harness.ade.detached_operations import DetachedOperationService
from comx_harness.ade.omx_team_native import OmxTeamObserver
from comx_harness.ade.recipe_catalog import builtin_recipes
from comx_harness.ade.run_projection import WorkspaceRunProjectionReader
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.workspace_service import WorkspaceService
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.ade_agent_schemas import (
    AdoptWorkspaceRequest,
    AgentContextRequest,
    AgentPlatformContext,
    AgentWorkspaceContext,
    CreateWorktreeRequest,
    ProjectReference,
    ProjectWorkspaceRegistration,
    RegisterProjectRequest,
    WorkspaceCollection,
    WorkspaceReference,
)
from comx_harness.schemas.ade_operator_schemas import WorkspaceRunProjection
from comx_harness.schemas.ade_schemas import AdeStateSettings, WorkspaceStatus
from comx_harness.schemas.provider_schemas import CapabilityReport
from comx_harness.shared.exceptions.harness_exceptions import HarnessError
from comx_harness.shared.exceptions.provider_exceptions import ProviderUnavailableError
from pydantic import ValidationError


class AdeAgentTools:
    """Typed non-GUI ADE application surface for trusted local agents."""

    def __init__(
        self,
        *,
        state_root: str | Path | None = None,
        tools: HarnessTools | None = None,
    ) -> None:
        settings = (
            AdeStateSettings(state_root=Path(state_root).expanduser().resolve())
            if state_root is not None
            else AdeStateSettings.from_environment()
        )
        self._store = AdeStateStore(settings)
        self._operations = DetachedOperationService(settings.state_root)
        self._workspaces = WorkspaceService(self._store)
        self._tools = tools or HarnessTools()

    def context(self, request: AgentContextRequest) -> AgentPlatformContext:
        catalog = self._store.load_catalog()
        view = self._store.load_view_context()
        workspace_contexts = tuple(
            self._workspace_context(
                workspace.workspace_id,
                limit=request.limit_per_workspace,
            )
            for workspace in catalog.workspaces
        )
        capabilities, capability_error = self._capabilities()
        return AgentPlatformContext(
            catalog=catalog,
            active_project_id=view.active_project_id,
            active_workspace_id=view.active_workspace_id,
            capabilities=capabilities,
            capability_error=capability_error,
            recipes=builtin_recipes(),
            workspaces=workspace_contexts,
            operations=self._operations.list_records(),
            attention_count=sum(
                len(run.attention)
                for workspace in workspace_contexts
                for run in workspace.runs.runs
            ),
        )

    def register_project(
        self,
        request: RegisterProjectRequest,
    ) -> ProjectWorkspaceRegistration:
        project = self._workspaces.register_project(request.path, name=request.name)
        workspace = self._workspaces.adopt_workspace(
            project.project_id,
            request.path,
            name=request.name,
        )
        return ProjectWorkspaceRegistration(project=project, workspace=workspace)

    def adopt_workspace(self, request: AdoptWorkspaceRequest) -> WorkspaceCollection:
        workspace = self._workspaces.adopt_workspace(
            request.project_id,
            request.path,
            name=request.name,
        )
        return WorkspaceCollection(workspaces=(workspace,))

    def create_worktree(self, request: CreateWorktreeRequest) -> WorkspaceCollection:
        workspace = self._workspaces.create_managed_worktree(
            request.project_id,
            branch=request.branch,
            name=request.name,
        )
        return WorkspaceCollection(workspaces=(workspace,))

    def discover_worktrees(self, request: ProjectReference) -> WorkspaceCollection:
        return WorkspaceCollection(
            workspaces=self._workspaces.discover_worktrees(request.project_id)
        )

    def inspect_workspace(self, request: WorkspaceReference) -> WorkspaceStatus:
        return self._workspaces.inspect_workspace(request.workspace_id)

    def _workspace_context(
        self,
        workspace_id: str,
        *,
        limit: int,
    ) -> AgentWorkspaceContext:
        status = self._workspaces.inspect_workspace(workspace_id)
        workspace = status.workspace
        if status.missing:
            projection = WorkspaceRunProjection(workspace=workspace.root_path, runs=())
        else:
            projection = WorkspaceRunProjectionReader(
                self._tools,
                team_observer=OmxTeamObserver(workspace.root_path),
            ).read(workspace.root_path, limit=limit)
        return AgentWorkspaceContext(status=status, runs=projection)

    def _capabilities(self) -> tuple[CapabilityReport | None, str | None]:
        try:
            return self._tools.capabilities(), None
        except (
            HarnessError,
            ProviderUnavailableError,
            ValidationError,
            OSError,
            ValueError,
        ) as error:
            return None, str(error) or type(error).__name__
