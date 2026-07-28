from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from comx_harness.ade.tk_app import AdeTkApplication
from comx_harness.ade.tk_attention import AttentionPane, _attention_tag
from comx_harness.ade.tk_refresh import AttentionSelection, _attention_entries
from comx_harness.schemas.ade_operator_schemas import (
    AttentionItem,
    AttentionTarget,
    RunSummary,
    WorkspaceRunProjection,
)
from comx_harness.schemas.ade_schemas import WorkspaceRecord
from comx_harness.shared.harness_enums.lifecycle_enums import (
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.operator_enums import (
    AttentionEntityKind,
    AttentionKind,
    RunDetailTab,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId


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
    app._refresh_all = MagicMock()
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
    app._refresh_all.assert_called_once_with()
    app._inspect_run.assert_called_once_with()
    assert app._pending_attention_target == target
    app.ui.detail.focus_attention_target.assert_not_called()


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
        opened.append,
    )
    pane._targets["attention:3"] = AttentionSelection(
        workspace=workspace,
        run_id="run-4",
        target=target,
    )

    pane.open_selected(None)  # type: ignore[arg-type]

    assert opened == [
        AttentionSelection(
            workspace=workspace,
            run_id="run-4",
            target=target,
        )
    ]


@pytest.mark.parametrize(
    ("kind", "expected_tag"),
    (
        (AttentionKind.APPROVAL_REQUIRED, "attention"),
        (AttentionKind.INPUT_REQUIRED, "attention"),
        (AttentionKind.ARTIFACT_ISSUE, "attention"),
        (AttentionKind.BLOCKED, "failure"),
        (AttentionKind.FAILED, "failure"),
        (AttentionKind.STALE, "failure"),
        (AttentionKind.READY_FOR_REVIEW, "success"),
    ),
)
def test_attention_kind_has_explicit_visual_state(
    kind: AttentionKind,
    expected_tag: str,
) -> None:
    assert _attention_tag(kind) == expected_tag


def test_attention_refresh_promotes_pydantic_enum_value_to_typed_kind() -> None:
    target = AttentionTarget(
        tab=RunDetailTab.OVERVIEW,
        entity_kind=AttentionEntityKind.RUN,
        entity_id="run-failed",
    )
    workspace = WorkspaceRecord(
        workspace_id="workspace-1",
        project_id="project-1",
        name="adapter",
        root_path="/tmp/adapter",
        kind="adopted_directory",
        created_at="2026-07-28T00:00:00Z",
    )
    projection = WorkspaceRunProjection(
        workspace=workspace.root_path,
        runs=(
            RunSummary(
                run_id="run-failed",
                provider=ProviderId.CODEX,
                objective="Verify the adapter",
                status=RunStatus.FAILED,
                liveness=ProcessLiveness.FINISHED,
                verified_artifact_count=0,
                attention=(
                    AttentionItem(
                        kind=AttentionKind.FAILED,
                        message="Tests failed.",
                        evidence="run record",
                        target=target,
                    ),
                ),
            ),
        ),
    )

    entries = _attention_entries(workspace, projection, set())

    assert entries[0].kind is AttentionKind.FAILED
