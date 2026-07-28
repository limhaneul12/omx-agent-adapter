from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from comx_harness.ade.controller import AdeController
from comx_harness.ade.external_tools import ExternalToolService
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.tk_shell import AdeTkShell
from comx_harness.ade.workspace_service import WorkspaceService
from comx_harness.schemas.ade_schemas import WorkspaceRecord


class TkProjectApplication:
    """Project, Workspace, Worktree, and external-opening application slice."""

    def __init__(
        self,
        initial_workspace: str | Path,
        *,
        state_store: AdeStateStore | None = None,
    ) -> None:
        self._initial_workspace = Path(initial_workspace).expanduser().resolve()
        self._store = state_store or AdeStateStore()
        self._workspaces = WorkspaceService(self._store)
        self._external = ExternalToolService()
        self._controller: AdeController | None = None
        self._active_workspace: WorkspaceRecord | None = None
        self._context = self._store.load_view_context()
        self.root = tk.Tk()
        self.ui: AdeTkShell

    def _ensure_initial_project(self) -> None:
        project = self._workspaces.register_project(self._initial_workspace)
        workspace = self._workspaces.adopt_workspace(
            project.project_id,
            self._initial_workspace,
        )
        with suppress(FileNotFoundError, OSError):
            # Non-Git directories remain valid Projects; worktree discovery is optional.
            self._workspaces.discover_worktrees(project.project_id)
        if self._context.active_workspace_id is None:
            self._context = self._context.model_copy(
                update={
                    "active_project_id": project.project_id,
                    "active_workspace_id": workspace.workspace_id,
                }
            )

    def _restore_context(self) -> None:
        catalog = self._store.load_catalog()
        workspace = next(
            (
                item
                for item in catalog.workspaces
                if item.workspace_id == self._context.active_workspace_id
            ),
            catalog.workspaces[0] if catalog.workspaces else None,
        )
        if workspace is not None:
            self._activate_workspace(workspace)
        self.ui.detail.select_tab(self._context.active_detail_tab)

    def _activate_workspace(self, workspace: WorkspaceRecord) -> None:
        self._active_workspace = workspace
        self._controller = AdeController(workspace.root_path, self._store.state_root)
        self.ui.workspace_label.configure(text=workspace.root_path)
        self._context = self._context.model_copy(
            update={
                "active_project_id": workspace.project_id,
                "active_workspace_id": workspace.workspace_id,
            }
        )
        self._store.save_view_context(self._context)

    def _refresh_sidebar(self) -> None:
        catalog = self._store.load_catalog()
        self.ui.sidebar.delete(*self.ui.sidebar.get_children())
        for project in catalog.projects:
            parent = f"project:{project.project_id}"
            self.ui.sidebar.insert("", "end", iid=parent, text=project.name, open=True)
            for workspace in catalog.workspaces:
                if workspace.project_id != project.project_id:
                    continue
                status = self._workspaces.inspect_workspace(workspace.workspace_id)
                label = (
                    f"{workspace.name} · {status.branch or 'not-git'}"
                    f"{' • dirty' if status.dirty else ''}"
                    f"{' • missing' if status.missing else ''}"
                )
                self.ui.sidebar.insert(
                    parent,
                    "end",
                    iid=f"workspace:{workspace.workspace_id}",
                    text=label,
                )
        if self._active_workspace is not None:
            selected = f"workspace:{self._active_workspace.workspace_id}"
            if self.ui.sidebar.exists(selected):
                self.ui.sidebar.selection_set(selected)

    def _sidebar_selected(self, event: tk.Event[tk.Misc]) -> None:
        del event
        selection = self.ui.sidebar.selection()
        if not selection or not selection[0].startswith("workspace:"):
            return
        workspace_id = selection[0].split(":", 1)[1]
        workspace = next(
            item
            for item in self._store.load_catalog().workspaces
            if item.workspace_id == workspace_id
        )
        if self._active_workspace != workspace:
            self._activate_workspace(workspace)
            self._workspace_changed()

    def _register_project(self) -> None:
        selected = filedialog.askdirectory(title="Register Project")
        if not selected:
            return
        try:
            project = self._workspaces.register_project(Path(selected))
            workspace = self._workspaces.adopt_workspace(
                project.project_id, Path(selected)
            )
            with suppress(FileNotFoundError, OSError):
                self._workspaces.discover_worktrees(project.project_id)
        except Exception as error:
            self._show_error("Project registration failed", error)
            return
        self._activate_workspace(workspace)
        self._refresh_all()

    def _adopt_workspace(self) -> None:
        active = self._require_workspace()
        selected = filedialog.askdirectory(title="Adopt Existing Workspace")
        if not selected:
            return
        try:
            workspace = self._workspaces.adopt_workspace(
                active.project_id,
                Path(selected),
            )
        except Exception as error:
            self._show_error("Workspace adoption failed", error)
            return
        self._activate_workspace(workspace)
        self._refresh_all()

    def _create_worktree(self) -> None:
        active = self._require_workspace()
        branch = simpledialog.askstring(
            "Create Isolated Worktree",
            "New branch name:",
            parent=self.root,
        )
        if not branch:
            return
        try:
            workspace = self._workspaces.create_managed_worktree(
                active.project_id,
                branch=branch,
            )
        except Exception as error:
            self._show_error("Worktree creation failed", error)
            return
        self._activate_workspace(workspace)
        self._refresh_all()

    def _open_finder(self) -> None:
        workspace = self._require_workspace()
        launch = self._external.launch(
            self._external.finder_target(workspace.root_path)
        )
        self.ui.status.set(launch.message or f"Finder launch pid={launch.pid}.")

    def _open_editor(self) -> None:
        workspace = self._require_workspace()
        application = simpledialog.askstring(
            "External Editor",
            "macOS application name:",
            initialvalue="Visual Studio Code",
            parent=self.root,
        )
        if not application:
            return
        launch = self._external.launch(
            self._external.editor_target(
                workspace.root_path,
                application=application,
            )
        )
        self.ui.status.set(launch.message or f"Editor launch pid={launch.pid}.")

    def _open_terminal(self) -> None:
        workspace = self._require_workspace()
        launch = self._external.launch(
            self._external.terminal_target(workspace.root_path)
        )
        self.ui.status.set(launch.message or f"Terminal launch pid={launch.pid}.")

    def _require_workspace(self) -> WorkspaceRecord:
        if self._active_workspace is None:
            raise RuntimeError("select a Workspace first")
        return self._active_workspace

    def _workspace_changed(self) -> None:
        """Let the Run slice clear selection and refresh after navigation."""
        raise NotImplementedError

    def _refresh_all(self) -> None:
        """Refresh every visible projection after a Project action."""
        raise NotImplementedError

    @staticmethod
    def _show_error(title: str, error: Exception) -> None:
        messagebox.showerror(title, str(error) or type(error).__name__)
