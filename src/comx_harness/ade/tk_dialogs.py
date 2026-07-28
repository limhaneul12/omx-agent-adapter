from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class MultilineInputDialog:
    """Modal multiline input for continuation and handoff objectives."""

    def __init__(self, parent: tk.Misc, *, title: str, prompt: str) -> None:
        self._value: str | None = None
        self._window = tk.Toplevel(parent)
        self._window.title(title)
        self._window.transient(parent.winfo_toplevel())
        self._window.grab_set()
        self._window.geometry("620x320")
        frame = ttk.Frame(self._window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=prompt, wraplength=560).pack(anchor="w")
        self._text = tk.Text(frame, wrap="word", undo=True)
        self._text.pack(fill="both", expand=True, pady=10)
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(actions, text="Continue", command=self._accept).pack(
            side="right",
            padx=8,
        )
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)
        self._text.focus_set()

    def ask(self) -> str | None:
        """Wait for explicit operator input without flattening newlines."""
        self._window.wait_window()
        return self._value

    def _accept(self) -> None:
        value = self._text.get("1.0", "end-1c").strip()
        self._value = value or None
        self._window.destroy()

    def _cancel(self) -> None:
        self._window.destroy()
