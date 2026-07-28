from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from comx_harness.ade.state_store import AdeStateStore
from comx_harness.schemas.ade_schemas import (
    AdeCatalog,
    ProjectRecord,
    WorkspaceKind,
    WorkspaceRecord,
    WorkspaceStatus,
)

_SAFE_DIRECTORY_CHARACTER = re.compile(r"[^A-Za-z0-9._-]+")


class WorkspaceService:
    """Project registration and local Git workspace management."""

    def __init__(self, store: AdeStateStore) -> None:
        self._store = store

    def register_project(
        self,
        path: Path,
        *,
        name: str | None = None,
    ) -> ProjectRecord:
        root_path = self._existing_directory(path)
        catalog = self._store.load_catalog()
        existing = next(
            (
                project
                for project in catalog.projects
                if project.root_path == str(root_path)
            ),
            None,
        )
        now = self._timestamp()
        if existing is not None:
            reopened = existing.model_copy(update={"last_opened_at": now})
            self._replace_project(catalog=catalog, project=reopened)
            return reopened
        project = ProjectRecord(
            project_id=uuid4().hex,
            name=name or root_path.name,
            root_path=str(root_path),
            created_at=now,
            last_opened_at=now,
        )
        self._store.save_catalog(
            AdeCatalog(
                projects=(*catalog.projects, project),
                workspaces=catalog.workspaces,
            )
        )
        return project

    def reopen_project(self, project_id: str) -> ProjectRecord:
        catalog = self._store.load_catalog()
        project = self._project(catalog=catalog, project_id=project_id)
        reopened = project.model_copy(update={"last_opened_at": self._timestamp()})
        self._replace_project(catalog=catalog, project=reopened)
        return reopened

    def adopt_workspace(
        self,
        project_id: str,
        path: Path,
        *,
        name: str | None = None,
    ) -> WorkspaceRecord:
        catalog = self._store.load_catalog()
        project = self._project(catalog=catalog, project_id=project_id)
        root_path = self._existing_directory(path)
        self._require_project_workspace(project=project, workspace_path=root_path)
        return self._upsert_workspace(
            catalog=catalog,
            project=project,
            root_path=root_path,
            kind="adopted_directory",
            name=name,
        )

    def discover_worktrees(self, project_id: str) -> tuple[WorkspaceRecord, ...]:
        catalog = self._store.load_catalog()
        project = self._project(catalog=catalog, project_id=project_id)
        completed = self._git(
            project.root_path,
            "worktree",
            "list",
            "--porcelain",
            "-z",
        )
        worktree_paths = self._parse_worktree_paths(completed.stdout)
        discovered: list[WorkspaceRecord] = []
        current_catalog = catalog
        for root_path in worktree_paths:
            kind: WorkspaceKind = (
                "managed_worktree"
                if self._is_relative_to(root_path, self._managed_project_root(project))
                else "discovered_worktree"
            )
            workspace = self._upsert_workspace(
                catalog=current_catalog,
                project=project,
                root_path=root_path,
                kind=kind,
                name=None,
            )
            discovered.append(workspace)
            current_catalog = self._store.load_catalog()
        return tuple(discovered)

    def create_managed_worktree(
        self,
        project_id: str,
        *,
        branch: str,
        name: str | None = None,
    ) -> WorkspaceRecord:
        catalog = self._store.load_catalog()
        project = self._project(catalog=catalog, project_id=project_id)
        self._git(project.root_path, "check-ref-format", "--branch", branch)
        directory_name = self._managed_directory_name(branch)
        root_path = self._managed_project_root(project) / directory_name
        if root_path.exists():
            raise FileExistsError(root_path)
        root_path.parent.mkdir(parents=True, exist_ok=True)
        self._git(
            project.root_path,
            "worktree",
            "add",
            "-b",
            branch,
            str(root_path),
        )
        return self._upsert_workspace(
            catalog=catalog,
            project=project,
            root_path=root_path.resolve(),
            kind="managed_worktree",
            name=name,
        )

    def inspect_workspace(self, workspace_id: str) -> WorkspaceStatus:
        catalog = self._store.load_catalog()
        workspace = self._workspace(catalog=catalog, workspace_id=workspace_id)
        root_path = Path(workspace.root_path)
        if not root_path.is_dir():
            return WorkspaceStatus(
                workspace=workspace,
                missing=True,
                git_repository=False,
                branch=None,
                dirty=None,
                observed_at=self._timestamp(),
            )
        repository_check = self._git_optional(
            root_path,
            "rev-parse",
            "--is-inside-work-tree",
        )
        is_git_repository = (
            repository_check.returncode == 0
            and repository_check.stdout.strip() == "true"
        )
        branch: str | None = None
        dirty: bool | None = None
        if is_git_repository:
            branch_result = self._git_optional(
                root_path,
                "symbolic-ref",
                "--short",
                "-q",
                "HEAD",
            )
            branch = (
                branch_result.stdout.strip() if branch_result.returncode == 0 else None
            )
            status_result = self._git(
                root_path,
                "status",
                "--porcelain",
                "--untracked-files=normal",
            )
            dirty = bool(status_result.stdout)
        return WorkspaceStatus(
            workspace=workspace,
            missing=False,
            git_repository=is_git_repository,
            branch=branch,
            dirty=dirty,
            observed_at=self._timestamp(),
        )

    def _replace_project(
        self,
        *,
        catalog: AdeCatalog,
        project: ProjectRecord,
    ) -> None:
        self._store.save_catalog(
            AdeCatalog(
                projects=tuple(
                    project if item.project_id == project.project_id else item
                    for item in catalog.projects
                ),
                workspaces=catalog.workspaces,
            )
        )

    def _upsert_workspace(
        self,
        *,
        catalog: AdeCatalog,
        project: ProjectRecord,
        root_path: Path,
        kind: WorkspaceKind,
        name: str | None,
    ) -> WorkspaceRecord:
        canonical_path = root_path.expanduser().resolve()
        existing = next(
            (
                workspace
                for workspace in catalog.workspaces
                if workspace.root_path == str(canonical_path)
            ),
            None,
        )
        if existing is not None:
            if existing.project_id != project.project_id:
                raise ValueError("workspace is registered to a different project")
            return existing
        workspace = WorkspaceRecord(
            workspace_id=uuid4().hex,
            project_id=project.project_id,
            name=name or canonical_path.name,
            root_path=str(canonical_path),
            kind=kind,
            created_at=self._timestamp(),
        )
        self._store.save_catalog(
            AdeCatalog(
                projects=catalog.projects,
                workspaces=(*catalog.workspaces, workspace),
            )
        )
        return workspace

    def _require_project_workspace(
        self,
        *,
        project: ProjectRecord,
        workspace_path: Path,
    ) -> None:
        project_path = Path(project.root_path)
        if self._is_relative_to(workspace_path, project_path):
            return
        project_common_dir = self._git_optional(
            project_path,
            "rev-parse",
            "--git-common-dir",
        )
        workspace_common_dir = self._git_optional(
            workspace_path,
            "rev-parse",
            "--git-common-dir",
        )
        if project_common_dir.returncode != 0 or workspace_common_dir.returncode != 0:
            raise ValueError("workspace is outside the registered project")
        project_git_path = self._canonical_git_path(
            working_directory=project_path,
            output=project_common_dir.stdout,
        )
        workspace_git_path = self._canonical_git_path(
            working_directory=workspace_path,
            output=workspace_common_dir.stdout,
        )
        if project_git_path != workspace_git_path:
            raise ValueError("workspace belongs to a different Git repository")

    def _managed_project_root(self, project: ProjectRecord) -> Path:
        return self._store.state_root / "worktrees" / project.project_id

    @staticmethod
    def _managed_directory_name(branch: str) -> str:
        normalized = _SAFE_DIRECTORY_CHARACTER.sub("-", branch).strip("-.")
        if not normalized:
            raise ValueError("branch does not produce a safe directory name")
        return normalized

    @staticmethod
    def _parse_worktree_paths(output: str) -> tuple[Path, ...]:
        return tuple(
            Path(token.removeprefix("worktree ")).resolve()
            for token in output.split("\0")
            if token.startswith("worktree ")
        )

    @staticmethod
    def _canonical_git_path(*, working_directory: Path, output: str) -> Path:
        git_path = Path(output.strip())
        if not git_path.is_absolute():
            git_path = working_directory / git_path
        return git_path.resolve()

    @staticmethod
    def _existing_directory(path: Path) -> Path:
        canonical_path = path.expanduser().resolve()
        if not canonical_path.is_dir():
            raise NotADirectoryError(canonical_path)
        return canonical_path

    @staticmethod
    def _project(*, catalog: AdeCatalog, project_id: str) -> ProjectRecord:
        for project in catalog.projects:
            if project.project_id == project_id:
                return project
        raise KeyError(f"unknown project: {project_id}")

    @staticmethod
    def _workspace(*, catalog: AdeCatalog, workspace_id: str) -> WorkspaceRecord:
        for workspace in catalog.workspaces:
            if workspace.workspace_id == workspace_id:
                return workspace
        raise KeyError(f"unknown workspace: {workspace_id}")

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        return path == parent or path.is_relative_to(parent)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _git(
        working_directory: str | Path,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", "-C", str(working_directory), *arguments),
            check=True,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _git_optional(
        working_directory: str | Path,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", "-C", str(working_directory), *arguments),
            check=False,
            capture_output=True,
            text=True,
        )
