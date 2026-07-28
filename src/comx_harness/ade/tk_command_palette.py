from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk

from comx_harness.ade.tk_shell import TkActionSet
from comx_harness.ade.tk_theme import PALETTE, theme_listbox

PaletteCommand = tuple[str, Callable[[], None]]


def open_ade_command_palette(root: tk.Tk, actions: TkActionSet) -> None:
    """Open the fixed ADE command catalog over the supplied UI actions."""
    commands = (
        ("New Run", actions.show_new_run),
        ("Refresh Workspace", actions.refresh),
        ("Register Project", actions.register_project),
        ("Adopt Workspace", actions.adopt_workspace),
        ("Create Isolated Worktree", actions.create_worktree),
        ("Inspect Selected Run", actions.inspect_run),
        ("Attach Observed OMX tmux", actions.attach_observed_tmux),
        ("Open Workspace Terminal", actions.open_terminal),
        ("Open Finder", actions.open_finder),
        ("Open External Editor", actions.open_editor),
        ("Cancel Selected Run", actions.cancel_run),
        ("Resume Selected Run", actions.resume_run),
        ("Handoff Selected Run", actions.handoff_run),
    )
    open_command_palette(root, commands)


def open_command_palette(
    root: tk.Tk,
    commands: Sequence[PaletteCommand],
) -> None:
    """Open a searchable mouse-and-keyboard command surface."""
    palette = tk.Toplevel(root)
    palette.title("Command Palette")
    palette.transient(root)
    palette.geometry("560x420")
    palette.configure(background=PALETTE.canvas)
    frame = ttk.Frame(palette, padding=12)
    frame.pack(fill="both", expand=True)
    query = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=query)
    entry.pack(fill="x")
    choices = tk.Listbox(frame, activestyle="dotbox")
    theme_listbox(choices)
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
