from types import SimpleNamespace
from unittest.mock import MagicMock

from comx_harness.ade.tk_app import AdeTkApplication
from comx_harness.ade.tk_attention import AttentionPane, AttentionSelection
from comx_harness.schemas.ade_operator_schemas import AttentionTarget
from comx_harness.shared.harness_enums.operator_enums import (
    AttentionEntityKind,
    RunDetailTab,
)


def test_attention_open_targets_exact_run_tab_and_entity() -> None:
    target = AttentionTarget(
        tab=RunDetailTab.TASKS,
        entity_kind=AttentionEntityKind.TASK,
        entity_id="task-7",
    )
    workspace = SimpleNamespace(workspace_id="workspace-1")
    app = object.__new__(AdeTkApplication)
    app.ui = SimpleNamespace(
        detail=SimpleNamespace(focus_attention_target=MagicMock()),
    )
    app._activate_workspace = MagicMock()
    app._refresh_workspace = MagicMock()
    app._inspect_run = MagicMock()

    app._open_attention_selection(
        AttentionSelection(
            workspace=workspace,
            run_id="run-9",
            target=target,
        )
    )

    app._activate_workspace.assert_called_once_with(workspace)
    assert app._selected_run_id == "run-9"
    app._refresh_workspace.assert_called_once_with()
    app._inspect_run.assert_called_once_with()
    app.ui.detail.focus_attention_target.assert_called_once_with(target)


def test_attention_pane_resolves_selected_workspace_evidence() -> None:
    target = AttentionTarget(
        tab=RunDetailTab.ARTIFACTS,
        entity_kind=AttentionEntityKind.ARTIFACT,
        entity_id="/tmp/verification.md",
    )
    workspace = SimpleNamespace(workspace_id="workspace-1")
    tree = SimpleNamespace(selection=lambda: ("attention:3",))
    opened: list[AttentionSelection] = []
    pane = AttentionPane(
        tree,
        SimpleNamespace(load_catalog=lambda: SimpleNamespace(workspaces=(workspace,))),
        opened.append,
    )
    pane._targets["attention:3"] = ("workspace-1", "run-4", target)

    pane.open_selected(None)  # type: ignore[arg-type]

    assert opened == [
        AttentionSelection(
            workspace=workspace,
            run_id="run-4",
            target=target,
        )
    ]
