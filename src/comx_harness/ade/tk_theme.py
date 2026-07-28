from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Literal


@dataclass(frozen=True, slots=True)
class AdePalette:
    canvas: str = "#0c0f14"
    rail: str = "#11151c"
    surface: str = "#171c24"
    elevated: str = "#1d2430"
    border: str = "#2a3342"
    border_active: str = "#46546b"
    text: str = "#edf1f7"
    muted: str = "#8f9bad"
    faint: str = "#657084"
    accent: str = "#7c6cff"
    accent_active: str = "#9185ff"
    selection: str = "#293047"
    working: str = "#58a6ff"
    success: str = "#44d17a"
    attention: str = "#f2b84b"
    failure: str = "#ff6577"


PALETTE = AdePalette()
UI_FONT = ("SF Pro Text", 12)
UI_SMALL_FONT = ("SF Pro Text", 11)
UI_TINY_FONT = ("SF Pro Text", 10)
UI_TITLE_FONT = ("SF Pro Display", 22, "bold")
UI_HEADER_FONT = ("SF Pro Display", 14, "bold")
UI_METRIC_FONT = ("SF Pro Display", 24, "bold")
UI_LABEL_FONT = ("SF Pro Text", 10, "bold")
MONO_FONT = ("Menlo", 11)


@dataclass(frozen=True, slots=True)
class ScrolledTextArea:
    container: ttk.Frame
    text: tk.Text


def configure_orca_theme(root: tk.Tk) -> None:
    """Configure one dark, dense developer-tool theme for every ttk surface."""
    root.configure(background=PALETTE.canvas)
    root.option_add("*tearOff", False)
    style = ttk.Style(root)
    theme = "clam" if "clam" in style.theme_names() else style.theme_use()
    style.theme_use(theme)
    style.configure(
        ".",
        background=PALETTE.canvas,
        foreground=PALETTE.text,
        fieldbackground=PALETTE.surface,
        bordercolor=PALETTE.border,
        darkcolor=PALETTE.border,
        lightcolor=PALETTE.border,
        troughcolor=PALETTE.rail,
        selectbackground=PALETTE.selection,
        selectforeground=PALETTE.text,
        font=UI_FONT,
    )
    style.configure("TFrame", background=PALETTE.canvas)
    style.configure("Rail.TFrame", background=PALETTE.rail)
    style.configure("Surface.TFrame", background=PALETTE.surface)
    style.configure("Elevated.TFrame", background=PALETTE.elevated)
    style.configure("TLabel", background=PALETTE.canvas, foreground=PALETTE.text)
    style.configure(
        "Rail.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.text,
    )
    style.configure(
        "Muted.TLabel",
        background=PALETTE.canvas,
        foreground=PALETTE.muted,
        font=UI_SMALL_FONT,
    )
    style.configure(
        "RailMuted.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.muted,
        font=UI_SMALL_FONT,
    )
    style.configure("Title.TLabel", font=UI_TITLE_FONT)
    style.configure("Header.TLabel", font=UI_HEADER_FONT)
    style.configure(
        "Brand.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.text,
        font=("SF Pro Display", 14, "bold"),
    )
    style.configure(
        "Accent.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.accent_active,
        font=("SF Pro Display", 15, "bold"),
    )
    style.configure(
        "WorkspacePath.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.muted,
        font=UI_TINY_FONT,
    )
    style.configure(
        "RailHeader.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.muted,
        font=UI_LABEL_FONT,
    )
    style.configure(
        "Section.TLabel",
        background=PALETTE.canvas,
        foreground=PALETTE.muted,
        font=UI_LABEL_FONT,
    )
    style.configure(
        "Metric.TLabel",
        background=PALETTE.elevated,
        foreground=PALETTE.text,
        font=UI_METRIC_FONT,
    )
    style.configure(
        "MetricLabel.TLabel",
        background=PALETTE.elevated,
        foreground=PALETTE.muted,
        font=UI_TINY_FONT,
    )
    style.configure(
        "Safety.TLabel",
        background=PALETTE.canvas,
        foreground=PALETTE.attention,
        font=UI_SMALL_FONT,
    )
    style.configure(
        "Provider.TLabel",
        background=PALETTE.elevated,
        foreground=PALETTE.muted,
        padding=(10, 5),
        font=UI_TINY_FONT,
    )
    style.configure(
        "Status.TLabel",
        background=PALETTE.rail,
        foreground=PALETTE.muted,
        padding=(14, 7),
        font=UI_TINY_FONT,
    )
    _configure_buttons(style)
    _configure_navigation(style)
    _configure_data_widgets(style)


def theme_text_widget(widget: tk.Text, monospace: bool = False) -> None:
    """Apply the shared dark treatment to a native Text widget."""
    widget.configure(
        background=PALETTE.surface,
        foreground=PALETTE.text,
        insertbackground=PALETTE.text,
        selectbackground=PALETTE.selection,
        selectforeground=PALETTE.text,
        highlightbackground=PALETTE.border,
        highlightcolor=PALETTE.accent,
        highlightthickness=1,
        relief="flat",
        borderwidth=0,
        padx=12,
        pady=10,
        font=MONO_FONT if monospace else UI_FONT,
    )


def create_scrolled_text_area(
    parent: tk.Misc,
    height: int = 24,
    wrap: Literal["none", "char", "word"] = "word",
    state: Literal["normal", "disabled"] = "normal",
    undo: bool = False,
    monospace: bool = False,
) -> ScrolledTextArea:
    """Build a themed Text surface with an explicit ttk scrollbar."""
    container = ttk.Frame(parent, style="Surface.TFrame")
    text = tk.Text(
        container,
        height=height,
        wrap=wrap,
        state=state,
        undo=undo,
    )
    scrollbar = ttk.Scrollbar(
        container,
        orient="vertical",
        command=text.yview,
        style="Dark.Vertical.TScrollbar",
    )
    text.configure(yscrollcommand=scrollbar.set)
    theme_text_widget(text, monospace=monospace)
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    area = ScrolledTextArea(container=container, text=text)
    return area


def theme_listbox(widget: tk.Listbox) -> None:
    """Apply the shared dark selection treatment to native Listbox widgets."""
    widget.configure(
        background=PALETTE.surface,
        foreground=PALETTE.text,
        selectbackground=PALETTE.selection,
        selectforeground=PALETTE.text,
        activestyle="none",
        highlightbackground=PALETTE.border,
        highlightcolor=PALETTE.accent,
        highlightthickness=1,
        relief="flat",
        borderwidth=0,
        font=UI_FONT,
    )


def _configure_buttons(style: ttk.Style) -> None:
    style.configure(
        "TButton",
        background=PALETTE.elevated,
        foreground=PALETTE.text,
        bordercolor=PALETTE.border,
        focuscolor=PALETTE.accent,
        padding=(12, 7),
        relief="flat",
        font=UI_SMALL_FONT,
    )
    style.map(
        "TButton",
        background=[
            ("pressed", PALETTE.selection),
            ("active", PALETTE.border),
            ("disabled", PALETTE.surface),
        ],
        foreground=[("disabled", PALETTE.faint)],
        bordercolor=[("focus", PALETTE.accent)],
    )
    style.configure(
        "Primary.TButton",
        background=PALETTE.accent,
        foreground="#ffffff",
        bordercolor=PALETTE.accent,
        padding=(14, 9),
        font=("SF Pro Text", 11, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[
            ("pressed", PALETTE.accent),
            ("active", PALETTE.accent_active),
            ("disabled", PALETTE.border),
        ],
        foreground=[("disabled", PALETTE.faint)],
    )
    style.configure(
        "Danger.TButton",
        foreground=PALETTE.failure,
        padding=(12, 7),
    )


def _configure_navigation(style: ttk.Style) -> None:
    style.configure(
        "TNotebook",
        background=PALETTE.canvas,
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=PALETTE.canvas,
        foreground=PALETTE.muted,
        borderwidth=0,
        padding=(16, 10),
        font=UI_SMALL_FONT,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE.surface), ("active", PALETTE.elevated)],
        foreground=[("selected", PALETTE.text), ("active", PALETTE.text)],
    )
    style.configure(
        "TPanedwindow",
        background=PALETTE.border,
        sashwidth=1,
    )
    style.configure(
        "TEntry",
        fieldbackground=PALETTE.surface,
        foreground=PALETTE.text,
        insertcolor=PALETTE.text,
        bordercolor=PALETTE.border,
        padding=(10, 8),
    )
    style.map("TEntry", bordercolor=[("focus", PALETTE.accent)])


def _configure_data_widgets(style: ttk.Style) -> None:
    style.configure(
        "Treeview",
        background=PALETTE.surface,
        fieldbackground=PALETTE.surface,
        foreground=PALETTE.text,
        bordercolor=PALETTE.border,
        rowheight=32,
        relief="flat",
        font=UI_SMALL_FONT,
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE.selection)],
        foreground=[("selected", PALETTE.text)],
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE.rail,
        foreground=PALETTE.muted,
        bordercolor=PALETTE.border,
        relief="flat",
        padding=(8, 8),
        font=UI_LABEL_FONT,
    )
    style.map(
        "Treeview.Heading",
        background=[("active", PALETTE.elevated)],
        foreground=[("active", PALETTE.text)],
    )
    style.configure(
        "Dark.Vertical.TScrollbar",
        background=PALETTE.border,
        darkcolor=PALETTE.border,
        lightcolor=PALETTE.border,
        troughcolor=PALETTE.surface,
        bordercolor=PALETTE.surface,
        arrowcolor=PALETTE.muted,
        relief="flat",
    )
    style.map(
        "Dark.Vertical.TScrollbar",
        background=[
            ("pressed", PALETTE.border_active),
            ("active", PALETTE.border_active),
        ],
    )
