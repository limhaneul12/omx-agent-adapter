from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk

PaletteCommand = tuple[str, Callable[[], None]]


def open_command_palette(
    root: tk.Tk,
    commands: Sequence[PaletteCommand],
) -> None:
    """Open a searchable mouse-and-keyboard command surface."""
    palette = tk.Toplevel(root)
    palette.title("Command Palette")
    palette.transient(root)
    palette.geometry("560x420")
    frame = ttk.Frame(palette, padding=12)
    frame.pack(fill="both", expand=True)
    query = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=query)
    entry.pack(fill="x")
    choices = tk.Listbox(frame, activestyle="dotbox")
    choices.pack(fill="both", expand=True, pady=(8, 0))

    def populate(*args: object) -> None:
        del args
        needle = query.get().casefold()
        choices.delete(0, "end")
        for label, _ in commands:
            if needle in label.casefold():
                choices.insert("end", label)
        if choices.size():
            choices.selection_set(0)

    def execute(event: tk.Event[tk.Misc] | None = None) -> None:
        del event
        selection = choices.curselection()
        if not selection:
            return
        label = choices.get(selection[0])
        palette.destroy()
        next(action for command, action in commands if command == label)()

    query.trace_add("write", populate)
    choices.bind("<Double-1>", execute)
    choices.bind("<Return>", execute)
    entry.bind("<Return>", execute)
    populate()
    entry.focus_set()
