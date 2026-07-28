from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk

from comx_harness.ade.tk_new_run_view import NewRunView
from comx_harness.ade.tk_run_detail_view import RunDetailView
from comx_harness.ade.tk_theme import PALETTE, configure_orca_theme
from comx_harness.schemas.ade_operator_schemas import Recipe

Action = Callable[[], None]


@dataclass(frozen=True, slots=True)
class TkActionSet:
    """Named UI actions supplied by the application controller."""

    register_project: Action
    adopt_workspace: Action
    create_worktree: Action
    open_finder: Action
    open_editor: Action
    open_terminal: Action
    attach_observed_tmux: Action
    show_new_run: Action
    refresh: Action
    inspect_run: Action
    cancel_run: Action
    resume_run: Action
    handoff_run: Action
    review_plan: Action
    start_run: Action
    open_artifact: Action
    open_commands: Action


class AdeTkShell:
    """Responsive three-pane desktop widget hierarchy."""

    def __init__(
        self,
        root: tk.Tk,
        recipes: tuple[Recipe, ...],
        actions: TkActionSet,
    ) -> None:
        self.root = root
        self.actions = actions
        configure_orca_theme(self.root)
        self._build_menu()
        self._build_shell(recipes)

    def _build_menu(self) -> None:
        menu = tk.Menu(
            self.root,
            background=PALETTE.rail,
            foreground=PALETTE.text,
            activebackground=PALETTE.selection,
            activeforeground=PALETTE.text,
        )
        project_menu = tk.Menu(
            menu,
            tearoff=False,
            background=PALETTE.rail,
            foreground=PALETTE.text,
            activebackground=PALETTE.selection,
            activeforeground=PALETTE.text,
        )
        for label, action in (
            ("Register Project…", self.actions.register_project),
            ("Adopt Existing Workspace…", self.actions.adopt_workspace),
            ("Create Isolated Worktree…", self.actions.create_worktree),
        ):
            project_menu.add_command(label=label, command=action)
        project_menu.add_separator()
        for label, action in (
            ("Open Finder", self.actions.open_finder),
            ("Open External Editor", self.actions.open_editor),
            ("Open Workspace Terminal", self.actions.open_terminal),
        ):
            project_menu.add_command(label=label, command=action)
        menu.add_cascade(label="Project", menu=project_menu)
        run_menu = tk.Menu(
            menu,
            tearoff=False,
            background=PALETTE.rail,
            foreground=PALETTE.text,
            activebackground=PALETTE.selection,
            activeforeground=PALETTE.text,
        )
        for label, action in (
            ("New Run", self.actions.show_new_run),
            ("Refresh", self.actions.refresh),
            ("Cancel Selected", self.actions.cancel_run),
            ("Resume Selected…", self.actions.resume_run),
            ("Handoff Selected…", self.actions.handoff_run),
            ("Attach Observed OMX tmux", self.actions.attach_observed_tmux),
        ):
            run_menu.add_command(label=label, command=action)
        menu.add_cascade(label="Run", menu=run_menu)
        menu.add_command(label="Commands", command=self.actions.open_commands)
        self.root.configure(menu=menu)

    def _build_shell(self, recipes: tuple[Recipe, ...]) -> None:
        header = ttk.Frame(self.root, padding=(16, 11), style="Rail.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="◐", style="Accent.TLabel").pack(side="left")
        ttk.Label(header, text="COMX AGENT", style="Brand.TLabel").pack(
            side="left",
            padx=(7, 18),
        )
        self.workspace_label = ttk.Label(
            header,
            text="No Workspace selected",
            style="WorkspacePath.TLabel",
        )
        self.workspace_label.pack(side="left")
        ttk.Button(
            header,
            text="⌘  Commands",
            command=self.actions.open_commands,
        ).pack(side="right")
        self.capability_label = ttk.Label(
            header,
            text="Providers · checking…",
            style="Provider.TLabel",
        )
        self.capability_label.pack(side="right", padx=(0, 10))
        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True)
        sidebar = ttk.Frame(
            panes,
            width=260,
            padding=12,
            style="Rail.TFrame",
        )
        main = ttk.Frame(panes)
        attention = ttk.Frame(
            panes,
            width=340,
            padding=12,
            style="Rail.TFrame",
        )
        panes.add(sidebar, weight=0)
        panes.add(main, weight=6)
        panes.add(attention, weight=0)
        self._build_sidebar(sidebar)
        self._build_main(main, recipes)
        self._build_attention(attention)
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(
            self.root,
            textvariable=self.status,
            style="Status.TLabel",
        ).pack(fill="x")

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="WORKSPACES", style="RailHeader.TLabel").pack(
            anchor="w",
            pady=(2, 10),
        )
        ttk.Button(
            parent,
            text="+  New Run",
            command=self.actions.show_new_run,
            style="Primary.TButton",
        ).pack(
            fill="x",
            pady=(0, 12),
        )
        self.sidebar = ttk.Treeview(parent, show="tree", selectmode="browse")
        self.sidebar.pack(fill="both", expand=True)
        actions = ttk.Frame(parent)
        actions.configure(style="Rail.TFrame")
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(
            actions,
            text="+ Repo",
            command=self.actions.register_project,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="+ Worktree",
            command=self.actions.create_worktree,
        ).pack(side="left", padx=6)

    def _build_main(
        self,
        parent: ttk.Frame,
        recipes: tuple[Recipe, ...],
    ) -> None:
        self.main_tabs = ttk.Notebook(parent)
        self.main_tabs.pack(fill="both", expand=True)
        home = ttk.Frame(self.main_tabs, padding=(20, 18))
        self.main_tabs.add(home, text="Workspace")
        title_row = ttk.Frame(home)
        title_row.pack(fill="x")
        ttk.Label(title_row, text="Workspace", style="Title.TLabel").pack(side="left")
        ttk.Button(
            title_row,
            text="Refresh",
            command=self.actions.refresh,
        ).pack(side="right")
        ttk.Button(
            title_row,
            text="Inspect selected",
            command=self.actions.inspect_run,
        ).pack(side="right", padx=(0, 8))
        self.workspace_summary = tk.StringVar()
        ttk.Label(
            home,
            textvariable=self.workspace_summary,
            style="Muted.TLabel",
        ).pack(
            anchor="w",
            pady=(3, 16),
        )
        self._build_workspace_metrics(home)
        ttk.Label(home, text="RECENT RUNS", style="Section.TLabel").pack(
            anchor="w",
            pady=(18, 8),
        )
        self.runs = ttk.Treeview(
            home,
            columns=("status", "provider", "liveness", "objective"),
            show="headings",
            selectmode="browse",
        )
        for column, width in (
            ("status", 120),
            ("provider", 80),
            ("liveness", 95),
            ("objective", 360),
        ):
            self.runs.heading(column, text=column.upper())
            self.runs.column(column, width=width, stretch=column == "objective")
        self._configure_run_tags()
        self.runs.pack(fill="both", expand=True)
        home_actions = ttk.Frame(home)
        home_actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            home_actions,
            text="+  New Run",
            command=self.actions.show_new_run,
            style="Primary.TButton",
        ).pack(side="left")
        self.new_run = NewRunView(
            self.main_tabs,
            recipes=recipes,
            plan_action=self.actions.review_plan,
            start_action=self.actions.start_run,
        )
        self.main_tabs.add(self.new_run, text="New Run")
        self.detail = RunDetailView(
            self.main_tabs,
            terminal_action=self.actions.open_terminal,
            tmux_action=self.actions.attach_observed_tmux,
            finder_action=self.actions.open_finder,
            editor_action=self.actions.open_editor,
            cancel_action=self.actions.cancel_run,
            resume_action=self.actions.resume_run,
            handoff_action=self.actions.handoff_run,
            artifact_action=self.actions.open_artifact,
        )
        self.main_tabs.add(self.detail, text="Run Detail")

    def _build_attention(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="ATTENTION", style="RailHeader.TLabel").pack(
            anchor="w",
            pady=(2, 3),
        )
        ttk.Label(
            parent,
            text="Items that need a decision or review",
            style="RailMuted.TLabel",
            wraplength=280,
        ).pack(
            anchor="w",
            pady=(0, 12),
        )
        self.attention = ttk.Treeview(
            parent,
            columns=("kind", "workspace", "message"),
            show="headings",
            selectmode="browse",
        )
        self.attention.heading("kind", text="STATE")
        self.attention.heading("workspace", text="WORKSPACE")
        self.attention.heading("message", text="WHY")
        self.attention.column("kind", width=110, stretch=False)
        self.attention.column("workspace", width=105, stretch=False)
        self.attention.column("message", width=180)
        self.attention.tag_configure("attention", foreground=PALETTE.attention)
        self.attention.tag_configure("failure", foreground=PALETTE.failure)
        self.attention.tag_configure("success", foreground=PALETTE.success)
        self.attention.pack(fill="both", expand=True)
        ttk.Label(
            parent,
            text="↵  Open selected evidence",
            style="RailMuted.TLabel",
            wraplength=260,
        ).pack(anchor="w", pady=(8, 0))

    def _build_workspace_metrics(self, parent: ttk.Frame) -> None:
        metrics = ttk.Frame(parent)
        metrics.pack(fill="x")
        self.active_count = tk.StringVar(value="—")
        self.attention_count = tk.StringVar(value="—")
        self.completed_count = tk.StringVar(value="—")
        for label, value in (
            ("ACTIVE", self.active_count),
            ("NEEDS ATTENTION", self.attention_count),
            ("COMPLETED", self.completed_count),
        ):
            card = ttk.Frame(metrics, padding=(14, 11), style="Elevated.TFrame")
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ttk.Label(card, textvariable=value, style="Metric.TLabel").pack(anchor="w")
            ttk.Label(card, text=label, style="MetricLabel.TLabel").pack(anchor="w")

    def _configure_run_tags(self) -> None:
        self.runs.tag_configure("working", foreground=PALETTE.working)
        self.runs.tag_configure("attention", foreground=PALETTE.attention)
        self.runs.tag_configure("succeeded", foreground=PALETTE.text)
        self.runs.tag_configure("failed", foreground=PALETTE.failure)
