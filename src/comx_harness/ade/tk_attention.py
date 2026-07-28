from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from comx_harness.ade.tk_refresh import (
    AttentionRefreshEntry,
    AttentionSelection,
)
from comx_harness.shared.harness_enums.operator_enums import AttentionKind


class AttentionPane:
    """Project actionable evidence into the global Attention tree."""

    def __init__(
        self,
        tree: ttk.Treeview,
        open_selection: Callable[[AttentionSelection], None],
    ) -> None:
        self._tree = tree
        self._open_selection = open_selection
        self._targets: dict[str, AttentionSelection] = {}

    def show(self, entries: tuple[AttentionRefreshEntry, ...]) -> None:
        """Render an already collected Attention projection on the Tk thread."""
        self._tree.delete(*self._tree.get_children())
        self._targets.clear()
        for sequence, entry in enumerate(entries):
            iid = f"attention:{sequence}"
            self._targets[iid] = entry.selection
            self._tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    _attention_label(entry.kind),
                    entry.workspace_name,
                    entry.message,
                ),
                tags=(_attention_tag(entry.kind),),
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
        selected = self._targets.get(selection[0])
        return selected


def _attention_label(kind: AttentionKind) -> str:
    label = kind.value.replace("_", " ").title()
    return label


def _attention_tag(kind: AttentionKind) -> str:
    if kind in {
        AttentionKind.BLOCKED,
        AttentionKind.FAILED,
        AttentionKind.STALE,
    }:
        return "failure"
    if kind == AttentionKind.READY_FOR_REVIEW:
        return "success"
    return "attention"
