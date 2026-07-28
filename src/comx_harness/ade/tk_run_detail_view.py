from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from comx_harness.ade.tk_theme import PALETTE, create_scrolled_text_area
from comx_harness.schemas.ade_inspection_schemas import (
    ArtifactContentProjection,
    GitDiffProjection,
)
from comx_harness.schemas.ade_operator_schemas import AttentionTarget, RunInspection
from comx_harness.schemas.omx_team_schemas import OmxTeamProjection


class RunDetailView(ttk.Frame):
    """Run-linked native and normalized inspection panes."""

    _TAB_NAMES = (
        "Overview",
        "Agents",
        "Tasks",
        "Activity",
        "Terminal",
        "Diff",
        "Artifacts",
        "Evidence",
    )

    def __init__(
        self,
        master: tk.Misc,
        terminal_action: Callable[[], None],
        tmux_action: Callable[[], None],
        finder_action: Callable[[], None],
        editor_action: Callable[[], None],
        cancel_action: Callable[[], None],
        resume_action: Callable[[], None],
        handoff_action: Callable[[], None],
        artifact_action: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=12)
        self._text_by_tab: dict[str, tk.Text] = {}
        self._artifact_action = artifact_action
        self._terminal_action = terminal_action
        self._tmux_action = tmux_action
        self._build_toolbar(
            terminal_action=terminal_action,
            tmux_action=tmux_action,
            finder_action=finder_action,
            editor_action=editor_action,
            cancel_action=cancel_action,
            resume_action=resume_action,
            handoff_action=handoff_action,
        )
        self._build_tabs()

    def show_inspection(
        self,
        inspection: RunInspection,
        diff: GitDiffProjection,
        team: OmxTeamProjection | None,
    ) -> None:
        """Render one Run and the current Workspace evidence around it."""
        record = inspection.state.record
        failure = record.failure.message if record.failure else "none"
        overview = (
            f"Run: {record.run_id}\n"
            f"Provider: {record.provider}\n"
            f"Status: {record.status}\n"
            f"Liveness: {inspection.state.liveness}\n"
            f"Session: {record.provider_session_id or 'unknown'}\n"
            f"Parent Run: {record.parent_run_id or 'none'}\n"
            f"Failure: {failure}\n\n"
            f"Objective\n{record.objective}"
        )
        self._replace("Overview", overview)
        self._replace("Activity", self._activity_text(inspection))
        self._replace("Artifacts", self._artifact_text(inspection))
        self._replace("Evidence", self._evidence_text(inspection))
        self._replace("Diff", self._diff_text(diff))
        self._replace(
            "Terminal",
            _terminal_text(team),
        )
        self._replace_team(team)

    def show_artifact_content(self, content: ArtifactContentProjection) -> None:
        """Show bounded selected Artifact content in its Run context."""
        body = content.text if content.text is not None else content.message
        self._replace(
            "Artifacts",
            f"{content.kind} · {content.state}\n{content.path}\n\n{body or ''}",
        )

    def active_tab(self) -> str:
        """Return the visible detail tab name for view-state restoration."""
        return self.notebook.tab(self.notebook.select(), "text")

    def select_tab(self, tab_name: str) -> None:
        """Restore a previously visible detail tab when it still exists."""
        for tab_id in self.notebook.tabs():
            if self.notebook.tab(tab_id, "text") == tab_name:
                self.notebook.select(tab_id)
                return

    def focus_attention_target(self, target: AttentionTarget) -> None:
        """Open the evidence tab and highlight its exact reported entity."""
        for text in self._text_by_tab.values():
            text.tag_remove("attention-target", "1.0", "end")
        tab_name = str(target.tab)
        self.select_tab(tab_name)
        text = self._text_by_tab[tab_name]
        index = text.search(target.entity_id, "1.0", stopindex="end")
        if not index:
            return
        text.tag_add(
            "attention-target",
            index,
            f"{index}+{len(target.entity_id)}c",
        )
        text.tag_configure(
            "attention-target",
            background=PALETTE.selection,
            foreground=PALETTE.text,
        )
        text.see(index)

    def _build_toolbar(
        self,
        terminal_action: Callable[[], None],
        tmux_action: Callable[[], None],
        finder_action: Callable[[], None],
        editor_action: Callable[[], None],
        cancel_action: Callable[[], None],
        resume_action: Callable[[], None],
        handoff_action: Callable[[], None],
    ) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(toolbar, text="Run Detail", style="Title.TLabel").pack(side="left")
        for label, action in (
            ("Attach OMX tmux", tmux_action),
            ("Workspace Terminal", terminal_action),
            ("Finder", finder_action),
            ("Editor", editor_action),
            ("Cancel", cancel_action),
            ("Resume", resume_action),
            ("Handoff", handoff_action),
        ):
            style = "Danger.TButton" if label == "Cancel" else "TButton"
            ttk.Button(toolbar, text=label, command=action, style=style).pack(
                side="right",
                padx=(6, 0),
            )

    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        for name in self._TAB_NAMES:
            frame = ttk.Frame(self.notebook, padding=8)
            text_area = create_scrolled_text_area(
                frame,
                wrap="none" if name in {"Activity", "Diff", "Artifacts"} else "word",
                state="disabled",
                monospace=True,
            )
            text = text_area.text
            text_area.container.pack(fill="both", expand=True)
            self._text_by_tab[name] = text
            if name == "Artifacts":
                ttk.Button(
                    frame,
                    text="Open first available Artifact",
                    command=self._artifact_action,
                ).pack(anchor="e", pady=(8, 0))
            if name == "Terminal":
                terminal_actions = ttk.Frame(frame)
                terminal_actions.pack(anchor="e", pady=(8, 0))
                ttk.Button(
                    terminal_actions,
                    text="Attach Observed OMX tmux",
                    command=self._tmux_action,
                ).pack(side="left")
                ttk.Button(
                    terminal_actions,
                    text="Open Workspace Terminal",
                    command=self._terminal_action,
                ).pack(side="left", padx=(8, 0))
            self.notebook.add(frame, text=name)

    def _replace(self, tab_name: str, value: str) -> None:
        text = self._text_by_tab[tab_name]
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("1.0", value)
        text.configure(state="disabled")

    def _replace_team(self, team: OmxTeamProjection | None) -> None:
        if team is None:
            unknown = "Native Agent and Task topology is unknown for this Run."
            self._replace("Agents", unknown)
            self._replace("Tasks", unknown)
            return
        workers = "\n".join(
            (
                f"{worker.name} · {worker.role} · {worker.state} · "
                f"alive={worker.alive} · task={worker.current_task_id or 'none'}"
            )
            for worker in team.workers
        )
        tasks = "\n".join(
            (
                f"{task.task_id} · {task.status} · owner={task.owner or 'unassigned'}"
                f"\n  {task.subject}"
            )
            for task in team.tasks
        )
        self._replace("Agents", workers or team.detail)
        self._replace("Tasks", tasks or "No native Tasks were reported.")

    @staticmethod
    def _activity_text(inspection: RunInspection) -> str:
        return (
            "\n".join(
                (
                    f"{event.sequence:04d} {event.timestamp} [{event.kind}] "
                    f"{event.message}"
                )
                for event in inspection.events.events
            )
            or "No normalized events are available."
        )

    @staticmethod
    def _artifact_text(inspection: RunInspection) -> str:
        return (
            "\n".join(
                (
                    f"{artifact.kind} · exists={artifact.exists} · "
                    f"required={artifact.required} · {artifact.size_bytes} bytes\n"
                    f"  {artifact.path}\n"
                    f"  sha256={artifact.sha256 or 'unknown'}"
                )
                for artifact in inspection.artifacts.artifacts
            )
            or "No Artifacts were reported."
        )

    @staticmethod
    def _evidence_text(inspection: RunInspection) -> str:
        verified = [
            artifact
            for artifact in inspection.artifacts.artifacts
            if artifact.exists and artifact.sha256 is not None
        ]
        if not verified:
            body = "Verification evidence is unknown or missing."
        else:
            body = "\n".join(
                f"VERIFIED · {artifact.kind} · {artifact.path}" for artifact in verified
            )
        return f"Run {inspection.state.record.run_id}\n{body}"

    @staticmethod
    def _diff_text(diff: GitDiffProjection) -> str:
        files = "\n".join(
            f"{item.staged_status or ' '}{item.unstaged_status or ' '} {item.path}"
            for item in diff.files
        )
        return (
            "Current Workspace diff; selected-Run attribution is unknown.\n"
            f"State: {diff.state}\n{diff.message or ''}\n\n"
            f"Changed files\n{files or 'none'}\n\n"
            f"Staged diff\n{diff.staged_diff or '(empty)'}\n\n"
            f"Unstaged diff\n{diff.unstaged_diff or '(empty)'}"
        )


def _terminal_text(team: OmxTeamProjection | None) -> str:
    if team is not None and team.available and team.tmux_session is not None:
        return (
            f"Observed OMX tmux session: {team.tmux_session}\n"
            "Attach uses this exact native identity; it is not inferred.\n\n"
            "Open Workspace Terminal remains an explicit generic fallback."
        )
    return (
        "No observed OMX tmux session identity is available for this Run.\n"
        "Attach is unavailable rather than inferred.\n\n"
        "Open Workspace Terminal is the explicit generic fallback."
    )
