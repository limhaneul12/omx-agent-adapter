from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import scrolledtext, ttk

from comx_harness.schemas.ade_operator_schemas import Recipe
from comx_harness.schemas.execution_schemas import ExecutionPlan
from comx_harness.shared.harness_enums.operator_enums import RecipeId


class NewRunView(ttk.Frame):
    """Discoverable multiline Run composer with an exact plan gate."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        recipes: tuple[Recipe, ...],
        plan_action: Callable[[], None],
        start_action: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=18)
        self._recipes = recipes
        self._plan_action = plan_action
        self._start_action = start_action
        self._description = tk.StringVar()
        self._safety = tk.StringVar()
        self._build()
        self._select_recipe(0)

    def recipe_id(self) -> RecipeId:
        """Return the visibly selected Recipe identity."""
        selection = self.recipe_list.curselection()
        index = selection[0] if selection else 0
        return RecipeId(self._recipes[index].recipe_id)

    def objective_text(self) -> str:
        """Return multiline objective text without flattening newlines."""
        return self.objective.get("1.0", "end-1c").strip()

    def show_plan(self, plan: ExecutionPlan) -> None:
        """Render the exact typed plan and enable its Run action."""
        self._replace_plan(plan.model_dump_json(indent=2))
        self.start_button.state(["!disabled"])

    def clear_plan(self) -> None:
        """Invalidate a preview after objective or Recipe changes."""
        self._replace_plan("Review a plan before starting this Run.")
        self.start_button.state(["disabled"])

    def focus_objective(self) -> None:
        """Move visible keyboard focus to the multiline editor."""
        self.objective.focus_set()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)
        ttk.Label(self, text="New Run", style="Title.TLabel").grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 12),
        )
        ttk.Label(self, text="Recipe").grid(row=1, column=0, sticky="nw")
        self.recipe_list = tk.Listbox(
            self,
            height=max(4, len(self._recipes)),
            exportselection=False,
            activestyle="dotbox",
        )
        for recipe in self._recipes:
            self.recipe_list.insert("end", recipe.title)
        self.recipe_list.grid(row=1, column=1, sticky="ew", padx=(12, 0))
        self.recipe_list.bind("<<ListboxSelect>>", self._recipe_changed)
        ttk.Label(self, textvariable=self._description, wraplength=720).grid(
            row=2,
            column=1,
            sticky="w",
            padx=(12, 0),
            pady=(6, 0),
        )
        ttk.Label(self, textvariable=self._safety, style="Safety.TLabel").grid(
            row=3,
            column=1,
            sticky="w",
            padx=(12, 0),
            pady=(3, 10),
        )
        ttk.Label(self, text="Objective").grid(row=4, column=0, sticky="nw")
        self.objective = scrolledtext.ScrolledText(
            self,
            height=9,
            wrap="word",
            undo=True,
        )
        self.objective.grid(row=4, column=1, sticky="nsew", padx=(12, 0))
        self.objective.bind("<<Modified>>", self._objective_changed)
        actions = ttk.Frame(self)
        actions.grid(row=5, column=1, sticky="ew", padx=(12, 0), pady=10)
        ttk.Button(actions, text="Review Plan", command=self._plan_action).pack(
            side="left"
        )
        self.start_button = ttk.Button(
            actions,
            text="Start Run",
            command=self._start_action,
            style="Primary.TButton",
        )
        self.start_button.pack(side="left", padx=8)
        self.start_button.state(["disabled"])
        ttk.Label(self, text="Exact provider and safety plan").grid(
            row=6,
            column=0,
            sticky="nw",
        )
        self.plan_text = scrolledtext.ScrolledText(
            self,
            height=12,
            wrap="none",
            state="disabled",
        )
        self.plan_text.grid(row=6, column=1, sticky="nsew", padx=(12, 0))
        self._replace_plan("Review a plan before starting this Run.")

    def _recipe_changed(self, event: tk.Event[tk.Misc]) -> None:
        del event
        selection = self.recipe_list.curselection()
        self._select_recipe(selection[0] if selection else 0)
        self.clear_plan()

    def _select_recipe(self, index: int) -> None:
        recipe = self._recipes[index]
        self.recipe_list.selection_clear(0, "end")
        self.recipe_list.selection_set(index)
        self._description.set(recipe.description)
        safety = "WORKSPACE WRITE" if recipe.mutation_allowed else "READ ONLY"
        self._safety.set(f"{recipe.provider.upper()} · {safety}")

    def _objective_changed(self, event: tk.Event[tk.Misc]) -> None:
        del event
        if self.objective.edit_modified():
            self.objective.edit_modified(False)
            self.clear_plan()

    def _replace_plan(self, value: str) -> None:
        self.plan_text.configure(state="normal")
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", value)
        self.plan_text.configure(state="disabled")
