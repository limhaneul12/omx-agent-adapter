import tkinter as tk
from collections.abc import Iterator
from contextlib import contextmanager
from gc import collect
from pathlib import Path
from threading import Event
from time import monotonic

import pytest
from comx_harness.ade.controller import AdeController
from comx_harness.ade.recipe_catalog import builtin_recipes
from comx_harness.ade.run_projection import WorkspaceRunProjectionReader
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.tk_app import AdeTkApplication
from comx_harness.ade.tk_new_run_view import NewRunView
from comx_harness.ade.tk_run_detail_view import RunDetailView, _terminal_text
from comx_harness.ade.tk_run_inspection import (
    RunInspectionReader,
    RunInspectionSnapshot,
)
from comx_harness.schemas.ade_inspection_schemas import GitDiffProjection
from comx_harness.schemas.ade_operator_schemas import (
    AttentionTarget,
    RunInspection,
    WorkspaceRunProjection,
)
from comx_harness.schemas.ade_schemas import AdeStateSettings
from comx_harness.schemas.artifact_schemas import ArtifactReport
from comx_harness.schemas.lifecycle_schemas import (
    EventReport,
    RunEvent,
    RunRecord,
    RunState,
)
from comx_harness.schemas.omx_team_schemas import OmxTeamProjection
from comx_harness.shared.harness_enums.lifecycle_enums import (
    EventKind,
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.operator_enums import (
    AttentionEntityKind,
    RunDetailTab,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId


@contextmanager
def _tk_root() -> Iterator[tk.Tk]:
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display is unavailable: {error}")
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()
        collect()


def test_new_run_view_preserves_multiline_objective_and_visible_plan_gate() -> None:
    with _tk_root() as root:
        planned: list[bool] = []
        started: list[bool] = []
        view = NewRunView(
            root,
            recipes=builtin_recipes(),
            plan_action=lambda: planned.append(True),
            start_action=lambda: started.append(True),
        )
        view.pack()
        view.objective.insert("1.0", "First line\nSecond line")
        root.update_idletasks()

        assert view.objective_text() == "First line\nSecond line"
        assert view.start_button.instate(["disabled"])
        view.focus_objective()
        assert root.focus_get() == view.objective


def test_application_startup_does_not_wait_for_slow_run_refresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    refresh_release = Event()

    def slow_projection(
        self: WorkspaceRunProjectionReader,
        workspace: str | Path,
        *,
        limit: int = 25,
    ) -> WorkspaceRunProjection:
        del self, limit
        refresh_release.wait(timeout=2)
        return WorkspaceRunProjection(workspace=str(workspace), runs=())

    monkeypatch.setattr(WorkspaceRunProjectionReader, "read", slow_projection)
    started = monotonic()
    try:
        application = AdeTkApplication(
            Path.cwd(),
            state_store=AdeStateStore(
                AdeStateSettings(state_root=tmp_path / "ade-state")
            ),
        )
    except tk.TclError as error:
        pytest.skip(f"Tk display is unavailable: {error}")
    startup_seconds = monotonic() - started
    try:
        application.root.withdraw()
        application._show_new_run()

        assert startup_seconds < 1
        assert application.ui.main_tabs.select() == str(application.ui.new_run)
    finally:
        refresh_release.set()
        application._close()
        collect()


def test_run_inspection_does_not_block_the_tk_event_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inspection_started = Event()
    inspection_release = Event()

    def slow_inspection(
        self: RunInspectionReader,
        controller: AdeController,
        run_id: str,
    ) -> RunInspectionSnapshot:
        del self, controller, run_id
        inspection_started.set()
        inspection_release.wait(timeout=2)
        raise RuntimeError("test inspection stopped")

    monkeypatch.setattr(RunInspectionReader, "read", slow_inspection)
    try:
        application = AdeTkApplication(
            Path.cwd(),
            state_store=AdeStateStore(
                AdeStateSettings(state_root=tmp_path / "ade-state")
            ),
        )
    except tk.TclError as error:
        pytest.skip(f"Tk display is unavailable: {error}")
    application._selected_run_id = "run-slow"
    started = monotonic()
    application._inspect_run()
    inspect_seconds = monotonic() - started
    try:
        application.root.withdraw()

        assert inspection_started.wait(timeout=1)
        assert inspect_seconds < 0.2
        assert application.ui.status.get() == "Inspecting run-slow…"
    finally:
        inspection_release.set()
        application._close()
        collect()


def test_run_detail_exposes_all_goal_tabs() -> None:
    with _tk_root() as root:

        def no_op() -> None:
            return None

        view = RunDetailView(
            root,
            terminal_action=no_op,
            tmux_action=no_op,
            finder_action=no_op,
            editor_action=no_op,
            cancel_action=no_op,
            resume_action=no_op,
            handoff_action=no_op,
            artifact_action=no_op,
        )
        view.pack()
        root.update_idletasks()

        labels = tuple(
            view.notebook.tab(tab_id, "text") for tab_id in view.notebook.tabs()
        )

        assert labels == (
            "Overview",
            "Agents",
            "Tasks",
            "Activity",
            "Terminal",
            "Diff",
            "Artifacts",
            "Evidence",
        )


def test_terminal_copy_distinguishes_observed_tmux_from_generic_fallback() -> None:
    team = OmxTeamProjection(
        team_name="alpha",
        status="running",
        available=True,
        detail="observed",
        tmux_session="omx-team-alpha",
    )

    observed = _terminal_text(team)
    unknown = _terminal_text(None)

    assert "Observed OMX tmux session: omx-team-alpha" in observed
    assert "exact native identity" in observed
    assert "Open Workspace Terminal" in observed
    assert "Attach is unavailable rather than inferred" in unknown


def test_run_detail_focuses_exact_attention_event() -> None:
    with _tk_root() as root:

        def no_op() -> None:
            return None

        view = RunDetailView(
            root,
            terminal_action=no_op,
            tmux_action=no_op,
            finder_action=no_op,
            editor_action=no_op,
            cancel_action=no_op,
            resume_action=no_op,
            handoff_action=no_op,
            artifact_action=no_op,
        )
        view.pack()
        record = RunRecord(
            run_id="run-1",
            owner_controller_id="human-operator",
            provider=ProviderId.CODEX,
            objective="Wait for approval",
            status=RunStatus.RUNNING,
            plan_path="plan.json",
        )
        view.show_inspection(
            RunInspection(
                state=RunState(
                    record=record,
                    liveness=ProcessLiveness.RUNNING,
                ),
                events=EventReport(
                    run_id=record.run_id,
                    events=(
                        RunEvent(
                            run_id=record.run_id,
                            sequence=7,
                            timestamp="2026-07-28T00:00:00Z",
                            kind=EventKind.PROVIDER,
                            message="approval.requested",
                            provider_event_type="approval.requested",
                        ),
                    ),
                ),
                artifacts=ArtifactReport(run_id=record.run_id, artifacts=()),
            ),
            GitDiffProjection(
                workspace="/tmp/workspace",
                state="unknown",
                message="not inspected",
            ),
            None,
        )

        view.focus_attention_target(
            AttentionTarget(
                tab=RunDetailTab.ACTIVITY,
                entity_kind=AttentionEntityKind.EVENT,
                entity_id="0007",
            )
        )
        root.update_idletasks()

        activity = view._text_by_tab["Activity"]
        ranges = activity.tag_ranges("attention-target")
        assert view.active_tab() == "Activity"
        assert activity.get(ranges[0], ranges[1]) == "0007"
