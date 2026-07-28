from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from comx_harness.ade.tk_new_run_view import NewRunView
from comx_harness.ade.tk_run_detail_view import RunDetailView
from comx_harness.schemas.ade_operator_schemas import Recipe

Action = Callable[[], None]


class TkActionSet:
    """Named UI actions supplied by the application controller."""

    def __init__(
        self,
        *,
        register_project: Action,
        adopt_workspace: Action,
        create_worktree: Action,
        open_finder: Action,
        open_editor: Action,
        open_terminal: Action,
        attach_observed_tmux: Action,
        show_new_run: Action,
        refresh: Action,
        inspect_run: Action,
        cancel_run: Action,
        resume_run: Action,
        handoff_run: Action,
        review_plan: Action,
        start_run: Action,
        open_artifact: Action,
        open_commands: Action,
    ) -> None:
        self.register_project = register_project
        self.adopt_workspace = adopt_workspace
        self.create_worktree = create_worktree
        self.open_finder = open_finder
        self.open_editor = open_editor
        self.open_terminal = open_terminal
        self.attach_observed_tmux = attach_observed_tmux
        self.show_new_run = show_new_run
        self.refresh = refresh
        self.inspect_run = inspect_run
        self.cancel_run = cancel_run
        self.resume_run = resume_run
        self.handoff_run = handoff_run
        self.review_plan = review_plan
        self.start_run = start_run
        self.open_artifact = open_artifact
        self.open_commands = open_commands


class AdeTkShell:
    """Responsive three-pane desktop widget hierarchy."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        recipes: tuple[Recipe, ...],
        actions: TkActionSet,
    ) -> None:
        self.root = root
        self.actions = actions
        self._configure_style()
        self._build_menu()
        self._build_shell(recipes)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        theme = "clam" if "clam" in style.theme_names() else style.theme_use()
        style.theme_use(theme)
        style.configure(".", font=("SF Pro Text", 12))
        style.configure("Title.TLabel", font=("SF Pro Display", 18, "bold"))
        style.configure("Header.TLabel", font=("SF Pro Display", 13, "bold"))
        style.configure("Primary.TButton", font=("SF Pro Text", 12, "bold"))
        style.configure("Safety.TLabel", foreground="#a04400")
        style.map(
            "Treeview",
            background=[("selected", "#315b8a")],
            foreground=[("selected", "#ffffff")],
        )

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        project_menu = tk.Menu(menu, tearoff=False)
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
        run_menu = tk.Menu(menu, tearoff=False)
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
        header = ttk.Frame(self.root, padding=(14, 10))
        header.pack(fill="x")
        ttk.Label(header, text="comx-agent", style="Title.TLabel").pack(side="left")
        self.workspace_label = ttk.Label(header, text="No Workspace selected")
        self.workspace_label.pack(side="left", padx=18)
        ttk.Button(
            header,
            text="Commands",
            command=self.actions.open_commands,
        ).pack(side="right")
        self.capability_label = ttk.Label(header, text="Providers: checking…")
        self.capability_label.pack(side="right", padx=16)
        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True)
        sidebar = ttk.Frame(panes, padding=10)
        main = ttk.Frame(panes)
        attention = ttk.Frame(panes, padding=10)
        panes.add(sidebar, weight=2)
        panes.add(main, weight=5)
        panes.add(attention, weight=3)
        self._build_sidebar(sidebar)
        self._build_main(main, recipes)
        self._build_attention(attention)
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self.root, textvariable=self.status, padding=(12, 6)).pack(fill="x")

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Projects & Workspaces", style="Header.TLabel").pack(
            anchor="w",
            pady=(0, 8),
        )
        self.sidebar = ttk.Treeview(parent, show="tree", selectmode="browse")
        self.sidebar.pack(fill="both", expand=True)
        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(
            actions,
            text="+ Project",
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
        home = ttk.Frame(self.main_tabs, padding=16)
        self.main_tabs.add(home, text="Workspace Home")
        ttk.Label(home, text="Workspace Home", style="Title.TLabel").pack(anchor="w")
        self.workspace_summary = tk.StringVar()
        ttk.Label(home, textvariable=self.workspace_summary).pack(
            anchor="w",
            pady=(4, 12),
        )
        self.runs = ttk.Treeview(
            home,
            columns=("provider", "status", "liveness", "objective"),
            show="headings",
            selectmode="browse",
        )
        for column, width in (
            ("provider", 80),
            ("status", 110),
            ("liveness", 100),
            ("objective", 560),
        ):
            self.runs.heading(column, text=column.title())
            self.runs.column(column, width=width, stretch=column == "objective")
        self.runs.pack(fill="both", expand=True)
        home_actions = ttk.Frame(home)
        home_actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            home_actions,
            text="New Run",
            command=self.actions.show_new_run,
        ).pack(side="left")
        ttk.Button(
            home_actions,
            text="Inspect Selected",
            command=self.actions.inspect_run,
        ).pack(side="left", padx=8)
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
        ttk.Label(parent, text="Attention", style="Header.TLabel").pack(
            anchor="w",
            pady=(0, 8),
        )
        self.attention = ttk.Treeview(
            parent,
            columns=("kind", "workspace", "message"),
            show="headings",
            selectmode="browse",
        )
        self.attention.heading("kind", text="State")
        self.attention.heading("workspace", text="Workspace")
        self.attention.heading("message", text="Why")
        self.attention.column("kind", width=130, stretch=False)
        self.attention.column("workspace", width=130, stretch=False)
        self.attention.column("message", width=260)
        self.attention.pack(fill="both", expand=True)
        ttk.Label(
            parent,
            text="Every item links to durable Run evidence.",
            wraplength=260,
        ).pack(anchor="w", pady=(8, 0))
