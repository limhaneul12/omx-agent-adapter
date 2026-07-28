from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.tk_app import AdeTkApplication
from comx_harness.schemas.ade_schemas import AdeStateSettings, AdeViewContext


class _FakeRuns:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self.selected: str | None = None

    def exists(self, run_id: str) -> bool:
        return run_id == self._run_id

    def selection_set(self, run_id: str) -> None:
        self.selected = run_id


class _FakeNotebook:
    def __init__(self) -> None:
        self.selected: object | None = None

    def select(self, target: object) -> None:
        self.selected = target


class _FakeDetail:
    def __init__(self) -> None:
        self.selected_tab: str | None = None

    def select_tab(self, label: str) -> None:
        self.selected_tab = label


def test_restart_restores_selected_run_main_view_and_detail_tab(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = AdeStateStore(AdeStateSettings(state_root=tmp_path))
    expected = AdeViewContext(
        active_project_id="project-1",
        active_workspace_id="workspace-1",
        active_view="run-detail",
        selected_run_id="run-1",
        active_detail_tab="Evidence",
    )
    store.save_view_context(expected)

    app = cast(Any, AdeTkApplication.__new__(AdeTkApplication))
    app._context = store.load_view_context()
    app._selected_run_id = app._context.selected_run_id
    runs = _FakeRuns("run-1")
    notebook = _FakeNotebook()
    detail = _FakeDetail()
    app.ui = SimpleNamespace(
        runs=runs,
        main_tabs=notebook,
        new_run=object(),
        detail=detail,
    )
    inspected: list[str] = []
    monkeypatch.setattr(
        app,
        "_inspect_run",
        lambda: inspected.append(app._selected_run_id),
    )

    app._restore_main_view()

    assert runs.selected == "run-1"
    assert inspected == ["run-1"]
    assert notebook.selected is detail
    assert detail.selected_tab == "Evidence"
