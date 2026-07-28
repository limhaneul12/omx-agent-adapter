from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from pathlib import Path
from tkinter import messagebox

from comx_harness.ade.artifact_content import ArtifactContentService
from comx_harness.ade.background_refresh import BackgroundRefreshCoordinator
from comx_harness.ade.controller import AdeController
from comx_harness.ade.diff_service import GitDiffService
from comx_harness.ade.recipe_catalog import builtin_recipes
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.tk_attention import AttentionPane
from comx_harness.ade.tk_command_palette import open_ade_command_palette
from comx_harness.ade.tk_dialogs import MultilineInputDialog
from comx_harness.ade.tk_project_application import TkProjectApplication
from comx_harness.ade.tk_refresh import (
    AdeRefreshReader,
    AdeRefreshRenderer,
    AdeRefreshSnapshot,
    AttentionSelection,
)
from comx_harness.ade.tk_run_inspection import (
    RunInspectionReader,
    RunInspectionSnapshot,
)
from comx_harness.ade.tk_runtime_helpers import (
    launch_observed_tmux as _launch_observed_tmux,
)
from comx_harness.ade.tk_shell import AdeTkShell, TkActionSet
from comx_harness.schemas.ade_operator_schemas import AttentionTarget, RunInspection


class AdeTkApplication(TkProjectApplication):
    """Native desktop shell over the shared Codex/OMX execution core."""

    def __init__(
        self,
        initial_workspace: str | Path,
        *,
        state_store: AdeStateStore | None = None,
    ) -> None:
        super().__init__(initial_workspace, state_store=state_store)
        self._artifact_content = ArtifactContentService()
        self._inspection_reader = RunInspectionReader(GitDiffService())
        self._selected_run_id = self._context.selected_run_id
        self._inspection: RunInspection | None = None
        self._pending_attention_target: AttentionTarget | None = None
        self._observed_tmux_session: str | None = None
        self._initial_view_pending = self._context.active_view == "run-detail"
        self.root.title("comx-agent · Codex & OMX ADE")
        self.root.minsize(980, 640)
        self.root.geometry(self._context.window_geometry or "1440x900")
        self.ui = AdeTkShell(
            self.root,
            recipes=builtin_recipes(),
            actions=self._actions(),
        )
        self._attention = AttentionPane(
            self.ui.attention,
            self._open_attention_selection,
        )
        self._refresh_reader = AdeRefreshReader(self._store)
        self._refresh_renderer = AdeRefreshRenderer(self.ui)
        self._background_refresh = BackgroundRefreshCoordinator[AdeRefreshSnapshot](
            schedule=self.root.after,
        )
        self._background_inspection = BackgroundRefreshCoordinator[
            RunInspectionSnapshot
        ](
            schedule=self.root.after,
        )
        self.ui.sidebar.bind("<<TreeviewSelect>>", self._sidebar_selected)
        self.ui.runs.bind("<Double-1>", self._run_opened)
        self.ui.runs.bind("<Return>", self._run_opened)
        self.ui.attention.bind("<Double-1>", self._attention.open_selected)
        self.ui.main_tabs.bind("<<NotebookTabChanged>>", self._main_view_changed)
        self._ensure_initial_project()
        self._restore_context()
        self._refresh_all()
        self._restore_main_view()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<Command-k>", self._open_commands)
        self.root.bind("<Control-k>", self._open_commands)
        self.root.after(1_500, self._scheduled_refresh)

    def run(self) -> None:
        """Run the native application event loop."""
        self.root.mainloop()

    def _actions(self) -> TkActionSet:
        return TkActionSet(
            register_project=self._register_project,
            adopt_workspace=self._adopt_workspace,
            create_worktree=self._create_worktree,
            open_finder=self._open_finder,
            open_editor=self._open_editor,
            open_terminal=self._open_terminal,
            attach_observed_tmux=self._attach_observed_tmux,
            show_new_run=self._show_new_run,
            refresh=self._refresh_all,
            inspect_run=self._inspect_run,
            cancel_run=self._cancel_run,
            resume_run=self._resume_run,
            handoff_run=self._handoff_run,
            review_plan=self._review_plan,
            start_run=self._start_run,
            open_artifact=self._open_first_artifact,
            open_commands=self._open_commands,
        )

    def _refresh_all(self) -> None:
        workspace_id = (
            self._active_workspace.workspace_id
            if self._active_workspace is not None
            else None
        )
        reviewed_run_ids = self._context.reviewed_run_ids
        self._background_refresh.request(
            load=lambda: self._refresh_reader.read(
                active_workspace_id=workspace_id,
                reviewed_run_ids=reviewed_run_ids,
            ),
            on_result=self._apply_refresh,
            on_error=self._refresh_failed,
        )

    def _workspace_changed(self) -> None:
        self._selected_run_id = None
        self._inspection = None
        self._pending_attention_target = None
        self._observed_tmux_session = None
        self._refresh_all()

    def _apply_refresh(self, snapshot: AdeRefreshSnapshot) -> None:
        workspace = self._active_workspace
        if workspace is None or snapshot.active_workspace_id != workspace.workspace_id:
            return
        self._refresh_renderer.apply(
            snapshot,
            active_workspace=workspace,
            selected_run_id=self._selected_run_id,
        )
        self._attention.show(snapshot.attention)
        if self._initial_view_pending:
            self._initial_view_pending = False
            self._restore_main_view()

    def _refresh_failed(self, error: Exception) -> None:
        self._initial_view_pending = False
        self.ui.status.set(f"Refresh failed: {str(error) or type(error).__name__}")

    def _show_new_run(self) -> None:
        self._initial_view_pending = False
        self.ui.main_tabs.select(self.ui.new_run)
        self.ui.new_run.focus_objective()

    def _restore_main_view(self) -> None:
        if self._context.active_view == "new-run":
            self.ui.main_tabs.select(self.ui.new_run)
            return
        if (
            self._context.active_view == "run-detail"
            and self._selected_run_id is not None
            and self.ui.runs.exists(self._selected_run_id)
        ):
            self.ui.runs.selection_set(self._selected_run_id)
            self._inspect_run()
            self.ui.main_tabs.select(self.ui.detail)
            self.ui.detail.select_tab(self._context.active_detail_tab)
            return
        if self._context.active_view == "run-detail" and self._initial_view_pending:
            self.ui.main_tabs.select(0)
            return
        if self._context.active_view == "run-detail":
            # Stale presentation state must not invent a Run that no longer exists.
            self._selected_run_id = None
        self.ui.main_tabs.select(0)

    def _main_view_changed(self, event: tk.Event[tk.Misc]) -> None:
        del event
        if self._initial_view_pending:
            if self.ui.main_tabs.select() == self.ui.main_tabs.tabs()[0]:
                return
            self._initial_view_pending = False
        selected = self.ui.main_tabs.select()
        active_view = (
            "new-run"
            if selected == str(self.ui.new_run)
            else "run-detail"
            if selected == str(self.ui.detail)
            else "workspace-home"
        )
        self._context = self._context.model_copy(update={"active_view": active_view})
        self._store.save_view_context(self._context)

    def _review_plan(self) -> None:
        objective = self.ui.new_run.objective_text()
        if not objective:
            messagebox.showinfo("Objective required", "Enter a multiline objective.")
            self.ui.new_run.focus_objective()
            return
        try:
            plan = self._require_controller().launch.plan(
                self.ui.new_run.recipe_id(),
                objective,
            )
        except Exception as error:
            self._show_error("Plan failed", error)
            return
        self.ui.new_run.show_plan(plan)
        self.ui.status.set(f"Plan {plan.run_id} is ready for review.")

    def _start_run(self) -> None:
        controller = self._require_controller()
        try:
            plan = controller.launch.planned_execution()
            operation = controller.launch.start_planned()
        except Exception as error:
            self._show_error("Run launch failed", error)
            return
        self._selected_run_id = plan.run_id if plan is not None else None
        self.ui.status.set(
            f"Detached {operation.operation_id} started; closing ADE will not cancel it."
        )
        self.ui.main_tabs.select(0)
        self._refresh_all()

    def _run_opened(self, event: tk.Event[tk.Misc]) -> None:
        del event
        self._inspect_run()

    def _inspect_run(self) -> None:
        selection = self.ui.runs.selection()
        if selection:
            self._selected_run_id = selection[0]
        run_id = self._selected_run_id
        if run_id is None:
            messagebox.showinfo("Select a Run", "Select a Run to inspect.")
            return
        controller = self._require_controller()
        self.ui.status.set(f"Inspecting {run_id}…")
        self._background_inspection.request(
            load=lambda: self._inspection_reader.read(controller, run_id),
            on_result=self._apply_inspection,
            on_error=self._inspection_failed,
        )

    def _apply_inspection(self, snapshot: RunInspectionSnapshot) -> None:
        controller = self._controller
        if (
            controller is None
            or controller.workspace != snapshot.workspace
            or self._selected_run_id != snapshot.run_id
        ):
            return
        inspection = snapshot.inspection
        team = snapshot.team
        self._inspection = inspection
        self._observed_tmux_session = (
            team.tmux_session
            if team is not None and team.available and team.tmux_session is not None
            else None
        )
        self.ui.detail.show_inspection(inspection, snapshot.diff, team)
        reviewed = tuple(
            dict.fromkeys((*self._context.reviewed_run_ids, snapshot.run_id))
        )
        self._context = self._context.model_copy(
            update={
                "selected_run_id": snapshot.run_id,
                "reviewed_run_ids": reviewed,
            }
        )
        self._store.save_view_context(self._context)
        self.ui.main_tabs.select(self.ui.detail)
        target = self._pending_attention_target
        self._pending_attention_target = None
        if target is not None:
            self.ui.detail.focus_attention_target(target)
        self.ui.status.set(f"Inspection ready: {snapshot.run_id}.")
        self._refresh_all()

    def _inspection_failed(self, error: Exception) -> None:
        self._pending_attention_target = None
        self._show_error("Inspection failed", error)

    def _cancel_run(self) -> None:
        if self._selected_run_id is None:
            messagebox.showinfo("Select a Run", "Select a Run to cancel.")
            return
        if not messagebox.askyesno(
            "Cancel Run",
            f"Request cancellation for {self._selected_run_id}?",
        ):
            return
        try:
            record = self._require_controller().control.cancel(self._selected_run_id)
        except Exception as error:
            self._show_error("Cancellation failed", error)
            return
        self.ui.status.set(f"Cancellation result: {record.status}.")
        self._refresh_all()

    def _resume_run(self) -> None:
        if self._selected_run_id is None:
            messagebox.showinfo("Select a Run", "Select a Run to resume.")
            return
        objective = MultilineInputDialog(
            self.root,
            title="Resume Run",
            prompt="Optional continuation objective. Leave blank to use the default.",
        ).ask()
        try:
            operation = self._require_controller().control.resume(
                self._selected_run_id,
                objective,
            )
        except Exception as error:
            self._show_error("Resume failed", error)
            return
        self.ui.status.set(f"Detached resume {operation.operation_id} started.")

    def _handoff_run(self) -> None:
        if self._selected_run_id is None:
            messagebox.showinfo("Select a Run", "Select a verified Run to hand off.")
            return
        objective = MultilineInputDialog(
            self.root,
            title="Cross-provider Handoff",
            prompt="Describe what the receiving provider must independently verify.",
        ).ask()
        if objective is None:
            return
        try:
            operation = self._require_controller().control.handoff(
                self._selected_run_id,
                objective,
            )
        except Exception as error:
            self._show_error("Handoff failed", error)
            return
        self.ui.status.set(f"Detached handoff {operation.operation_id} started.")

    def _open_first_artifact(self) -> None:
        inspection = self._inspection
        if inspection is None or not inspection.artifacts.artifacts:
            messagebox.showinfo("No Artifact", "This Run has no reported Artifact.")
            return
        artifact = next(
            (item for item in inspection.artifacts.artifacts if item.exists),
            inspection.artifacts.artifacts[0],
        )
        try:
            content = self._artifact_content.read(inspection.artifacts, artifact.path)
        except Exception as error:
            self._show_error("Artifact read failed", error)
            return
        self.ui.detail.show_artifact_content(content)

    def _open_attention_selection(self, selection: AttentionSelection) -> None:
        self._activate_workspace(selection.workspace)
        self._selected_run_id = selection.run_id
        self._pending_attention_target = selection.target
        self._refresh_all()
        self._inspect_run()

    def _open_commands(self, event: tk.Event[tk.Misc] | None = None) -> None:
        del event
        open_ade_command_palette(self.root, self.ui.actions)

    def _attach_observed_tmux(self) -> None:
        launch = _launch_observed_tmux(
            self._external,
            self._observed_tmux_session,
        )
        self.ui.status.set(
            launch.message or f"OMX tmux attach launched pid={launch.pid}."
        )

    def _scheduled_refresh(self) -> None:
        if not self.root.winfo_exists():
            return
        with suppress(RuntimeError, tk.TclError):
            # Native process and filesystem state may change between polling reads.
            self._refresh_all()
        self.root.after(1_500, self._scheduled_refresh)

    def _close(self) -> None:
        self._context = self._context.model_copy(
            update={
                "selected_run_id": self._selected_run_id,
                "active_view": self._active_main_view(),
                "active_detail_tab": self.ui.detail.active_tab(),
                "window_geometry": self.root.geometry(),
            }
        )
        self._store.save_view_context(self._context)
        self.root.withdraw()
        self._background_refresh.close()
        self._background_inspection.close()
        self.root.destroy()

    def _active_main_view(self) -> str:
        selected = self.ui.main_tabs.select()
        if selected == str(self.ui.new_run):
            return "new-run"
        if selected == str(self.ui.detail):
            return "run-detail"
        return "workspace-home"

    def _require_controller(self) -> AdeController:
        if self._controller is None:
            raise RuntimeError("select a Workspace first")
        return self._controller


def run_ade(workspace: str | Path = ".") -> None:
    """Launch the native desktop Agent Development Environment."""
    AdeTkApplication(workspace).run()
