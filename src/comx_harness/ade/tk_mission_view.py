from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from uuid import uuid4

from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.schemas.mission_schemas import MissionConstraints, MissionRequest
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    SandboxMode,
)
from comx_harness.shared.harness_enums.mission_enums import MissionExecutionProfile


class MissionView(ttk.Frame):
    """Thin Mission form; all planning and execution stay in MissionService."""

    def __init__(
        self,
        parent: ttk.Notebook,
        *,
        plan_action: Callable[[], None],
        execute_action: Callable[[], None],
    ) -> None:
        super().__init__(parent, padding=(20, 18))
        self._profile = tk.StringVar(value=MissionExecutionProfile.CODEX_NATIVE.value)
        self._mutation = tk.BooleanVar(value=False)
        self._sandbox = tk.StringVar(value=SandboxMode.READ_ONLY.value)
        self._approval = tk.StringVar(value=ApprovalPolicy.ON_REQUEST.value)
        self._timeout = tk.StringVar(value="3600")
        ttk.Label(self, text="Mission", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self, text="Objective", style="Section.TLabel").pack(
            anchor="w", pady=(14, 4)
        )
        self.objective = tk.Text(self, height=7, wrap="word")
        self.objective.pack(fill="x")
        options = ttk.Frame(self)
        options.pack(fill="x", pady=(12, 8))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        self._combo(
            options,
            "Profile",
            self._profile,
            tuple(item.value for item in MissionExecutionProfile),
            0,
            0,
        )
        self._combo(
            options,
            "Sandbox",
            self._sandbox,
            tuple(item.value for item in SandboxMode),
            0,
            1,
        )
        self._combo(
            options,
            "Approval",
            self._approval,
            tuple(item.value for item in ApprovalPolicy),
            2,
            0,
        )
        ttk.Label(options, text="Timeout (s)").grid(
            row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0)
        )
        ttk.Entry(options, textvariable=self._timeout, width=9).grid(
            row=3, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Checkbutton(
            options,
            text="Allow workspace mutation",
            variable=self._mutation,
            command=self._sync_mutation,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(4, 8))
        ttk.Button(buttons, text="Plan Mission", command=plan_action).pack(side="left")
        ttk.Button(
            buttons,
            text="Execute Mission",
            command=execute_action,
            style="Primary.TButton",
        ).pack(side="left", padx=8)
        ttk.Label(self, text="Compiled Strategy preview", style="Section.TLabel").pack(
            anchor="w", pady=(8, 4)
        )
        self.preview = tk.Text(self, height=16, wrap="none", state="disabled")
        self.preview.pack(fill="both", expand=True)

    def _combo(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        row: int,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(
            row=row, column=column, sticky="w", padx=(0, 8), pady=(8 if row else 0, 0)
        )
        ttk.Combobox(
            parent, textvariable=variable, values=values, state="readonly", width=22
        ).grid(row=row + 1, column=column, sticky="ew", padx=(0, 8))

    def _sync_mutation(self) -> None:
        self._sandbox.set(
            SandboxMode.WORKSPACE_WRITE.value
            if self._mutation.get()
            else SandboxMode.READ_ONLY.value
        )

    def request(self, workspace: str) -> MissionRequest:
        objective = self.objective.get("1.0", "end").strip()
        mission_id = f"gui-{uuid4().hex[:16]}"
        return MissionRequest(
            mission_id=mission_id,
            controller_id="human-gui",
            objective=objective,
            workspace=workspace,
            execution_profile=MissionExecutionProfile(self._profile.get()),
            constraints=MissionConstraints(mutation_allowed=self._mutation.get()),
            timeout_seconds=int(self._timeout.get()),
            options=RunOptions(
                sandbox=SandboxMode(self._sandbox.get()),
                approval_policy=ApprovalPolicy(self._approval.get()),
            ),
        )

    def show_plan(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def focus_objective(self) -> None:
        self.objective.focus_set()
