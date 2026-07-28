from __future__ import annotations

from pathlib import Path
from typing import Literal

from comx_harness.schemas.ade_inspection_schemas import DetachedOperationRecord
from comx_harness.schemas.ade_operator_schemas import Recipe, WorkspaceRunProjection
from comx_harness.schemas.ade_schemas import (
    AdeCatalog,
    ProjectRecord,
    WorkspaceRecord,
    WorkspaceStatus,
)
from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.schemas.provider_schemas import CapabilityReport
from pydantic import Field


class AgentContextRequest(StrictModel):
    limit_per_workspace: int = Field(default=25, ge=1, le=100)


class RegisterProjectRequest(StrictModel):
    path: Path
    name: NonEmptyString | None = None


class AdoptWorkspaceRequest(StrictModel):
    project_id: NonEmptyString
    path: Path
    name: NonEmptyString | None = None


class CreateWorktreeRequest(StrictModel):
    project_id: NonEmptyString
    branch: NonEmptyString
    name: NonEmptyString | None = None


class ProjectReference(StrictModel):
    project_id: NonEmptyString


class WorkspaceReference(StrictModel):
    workspace_id: NonEmptyString


class DetachedOperationReference(StrictModel):
    operation_id: NonEmptyString


class DetachedOperationCollection(StrictModel):
    schema_version: Literal["ade-detached-operation-collection.v1"] = (
        "ade-detached-operation-collection.v1"
    )
    operations: tuple[DetachedOperationRecord, ...]


class ProjectWorkspaceRegistration(StrictModel):
    schema_version: Literal["ade-project-workspace-registration.v1"] = (
        "ade-project-workspace-registration.v1"
    )
    project: ProjectRecord
    workspace: WorkspaceRecord


class WorkspaceCollection(StrictModel):
    schema_version: Literal["ade-workspace-collection.v1"] = (
        "ade-workspace-collection.v1"
    )
    workspaces: tuple[WorkspaceRecord, ...]


class AgentWorkspaceContext(StrictModel):
    schema_version: Literal["ade-agent-workspace-context.v1"] = (
        "ade-agent-workspace-context.v1"
    )
    status: WorkspaceStatus
    runs: WorkspaceRunProjection


class AgentPlatformContext(StrictModel):
    schema_version: Literal["ade-agent-platform-context.v1"] = (
        "ade-agent-platform-context.v1"
    )
    catalog: AdeCatalog
    active_project_id: NonEmptyString | None
    active_workspace_id: NonEmptyString | None
    capabilities: CapabilityReport | None
    capability_error: NonEmptyString | None
    recipes: tuple[Recipe, ...]
    workspaces: tuple[AgentWorkspaceContext, ...]
    operations: tuple[DetachedOperationRecord, ...]
    attention_count: int = Field(ge=0)
