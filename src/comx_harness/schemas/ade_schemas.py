from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from pydantic import model_validator

ADE_STATE_DIRECTORY_ENV = "COMX_AGENT_ADE_STATE_DIR"

WorkspaceKind = Literal[
    "adopted_directory",
    "discovered_worktree",
    "managed_worktree",
]


class AdeStateSettings(StrictModel):
    """Filesystem settings for local, single-user ADE application state."""

    state_root: Path

    @classmethod
    def from_environment(cls) -> AdeStateSettings:
        configured_root = os.environ.get(ADE_STATE_DIRECTORY_ENV)
        state_root = (
            Path(configured_root)
            if configured_root is not None
            else Path.home() / ".comx-agent" / "ade"
        )
        return cls(state_root=state_root.expanduser().resolve())


class ProjectRecord(StrictModel):
    schema_version: Literal["ade-project.v1"] = "ade-project.v1"
    project_id: NonEmptyString
    name: NonEmptyString
    root_path: NonEmptyString
    created_at: NonEmptyString
    last_opened_at: NonEmptyString


class WorkspaceRecord(StrictModel):
    schema_version: Literal["ade-workspace.v1"] = "ade-workspace.v1"
    workspace_id: NonEmptyString
    project_id: NonEmptyString
    name: NonEmptyString
    root_path: NonEmptyString
    kind: WorkspaceKind
    created_at: NonEmptyString


class AdeCatalog(StrictModel):
    schema_version: Literal["ade-catalog.v1"] = "ade-catalog.v1"
    projects: tuple[ProjectRecord, ...]
    workspaces: tuple[WorkspaceRecord, ...]

    @model_validator(mode="after")
    def reject_duplicate_identity(self) -> AdeCatalog:
        project_ids = [project.project_id for project in self.projects]
        project_paths = [project.root_path for project in self.projects]
        workspace_ids = [workspace.workspace_id for workspace in self.workspaces]
        workspace_paths = [workspace.root_path for workspace in self.workspaces]
        if len(project_ids) != len(set(project_ids)):
            raise ValueError("project_id values must be unique")
        if len(project_paths) != len(set(project_paths)):
            raise ValueError("project root paths must be unique")
        if len(workspace_ids) != len(set(workspace_ids)):
            raise ValueError("workspace_id values must be unique")
        if len(workspace_paths) != len(set(workspace_paths)):
            raise ValueError("workspace root paths must be unique")
        known_project_ids = set(project_ids)
        if any(
            workspace.project_id not in known_project_ids
            for workspace in self.workspaces
        ):
            raise ValueError("every workspace must reference a registered project")
        return self


class AdeViewContext(StrictModel):
    """Non-authoritative presentation state, separate from execution truth."""

    schema_version: Literal["ade-view-context.v1"] = "ade-view-context.v1"
    active_project_id: NonEmptyString | None = None
    active_workspace_id: NonEmptyString | None = None
    active_view: NonEmptyString = "projects"
    selected_run_id: NonEmptyString | None = None
    active_detail_tab: NonEmptyString = "Overview"
    window_geometry: NonEmptyString | None = None
    reviewed_run_ids: tuple[NonEmptyString, ...] = ()


class WorkspaceStatus(StrictModel):
    schema_version: Literal["ade-workspace-status.v1"] = "ade-workspace-status.v1"
    workspace: WorkspaceRecord
    missing: bool
    git_repository: bool
    branch: NonEmptyString | None
    dirty: bool | None
    observed_at: NonEmptyString
