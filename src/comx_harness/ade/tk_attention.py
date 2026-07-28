from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Collection
from dataclasses import dataclass
from tkinter import ttk

from comx_harness.ade.controller import AdeController
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.schemas.ade_operator_schemas import AttentionTarget
from comx_harness.schemas.ade_schemas import WorkspaceRecord


@dataclass(frozen=True, slots=True)
class AttentionSelection:
    workspace: WorkspaceRecord
    run_id: str
    target: AttentionTarget


class AttentionPane:
    """Project actionable evidence into the global Attention tree."""

    def __init__(
        self,
        tree: ttk.Treeview,
        store: AdeStateStore,
        open_selection: Callable[[AttentionSelection], None],
    ) -> None:
        self._tree = tree
        self._store = store
        self._open_selection = open_selection
        self._targets: dict[str, tuple[str, str, AttentionTarget]] = {}

    def refresh(self, reviewed_run_ids: Collection[str]) -> None:
        self._tree.delete(*self._tree.get_children())
        self._targets.clear()
        reviewed = set(reviewed_run_ids)
        sequence = 0
        for workspace in self._store.load_catalog().workspaces:
            controller = AdeController(
                workspace.root_path,
                self._store.state_root,
            )
            for run in controller.observe.projection().runs:
                for item in run.attention:
                    if run.run_id in reviewed and item.kind == "ready_for_review":
                        continue
                    iid = f"attention:{sequence}"
                    sequence += 1
                    self._targets[iid] = (
                        workspace.workspace_id,
                        run.run_id,
                        item.target,
                    )
                    self._tree.insert(
                        "",
                        "end",
                        iid=iid,
                        values=(
                            item.kind.replace("_", " ").title(),
                            workspace.name,
                            item.message,
                        ),
                    )

    def open_selected(self, event: tk.Event[tk.Misc]) -> None:
        del event
        selection = self._selected()
        if selection is not None:
            self._open_selection(selection)

    def _selected(self) -> AttentionSelection | None:
        selection = self._tree.selection()
        if not selection:
            return None
        target = self._targets.get(selection[0])
        if target is None:
            return None
        workspace_id, run_id, attention_target = target
        workspace = next(
            (
                item
                for item in self._store.load_catalog().workspaces
                if item.workspace_id == workspace_id
            ),
            None,
        )
        if workspace is None:
            return None
        return AttentionSelection(
            workspace=workspace,
            run_id=run_id,
            target=attention_target,
        )
