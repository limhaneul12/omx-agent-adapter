from pathlib import Path

import pytest
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.schemas.ade_schemas import (
    ADE_STATE_DIRECTORY_ENV,
    AdeCatalog,
    AdeStateSettings,
    AdeViewContext,
    ProjectRecord,
)
from pydantic import ValidationError


def test_default_and_environment_state_locations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv(ADE_STATE_DIRECTORY_ENV, raising=False)
    assert AdeStateSettings.from_environment().state_root == (
        tmp_path / ".comx-agent" / "ade"
    )

    configured_root = tmp_path / "custom-state"
    monkeypatch.setenv(ADE_STATE_DIRECTORY_ENV, str(configured_root))
    assert AdeStateSettings.from_environment().state_root == configured_root


def test_catalog_and_view_context_persist_separately_and_atomically(
    tmp_path: Path,
) -> None:
    store = AdeStateStore(AdeStateSettings(state_root=tmp_path))
    project = ProjectRecord(
        project_id="project-1",
        name="Example",
        root_path="/example",
        created_at="2026-07-28T00:00:00+00:00",
        last_opened_at="2026-07-28T00:00:00+00:00",
    )
    catalog = AdeCatalog(projects=(project,), workspaces=())
    context = AdeViewContext(
        active_project_id=project.project_id,
        active_workspace_id=None,
        active_view="workspace-home",
    )

    store.save_catalog(catalog)
    store.save_view_context(context)

    assert store.load_catalog() == catalog
    assert store.load_view_context() == context
    assert (tmp_path / "catalog.json").is_file()
    assert (tmp_path / "view-context.json").is_file()
    assert tuple(tmp_path.glob("*.tmp")) == ()
    assert tmp_path.stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "catalog.json").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "view-context.json").stat().st_mode & 0o777 == 0o600


def test_missing_files_return_explicit_empty_application_state(tmp_path: Path) -> None:
    store = AdeStateStore(AdeStateSettings(state_root=tmp_path))

    assert store.load_catalog() == AdeCatalog(projects=(), workspaces=())
    assert store.load_view_context() == AdeViewContext(
        active_project_id=None,
        active_workspace_id=None,
        active_view="projects",
    )


def test_failed_atomic_replace_preserves_previous_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = AdeStateStore(AdeStateSettings(state_root=tmp_path))
    original = AdeCatalog(projects=(), workspaces=())
    store.save_catalog(original)
    replacement = AdeCatalog(
        projects=(
            ProjectRecord(
                project_id="project-1",
                name="Example",
                root_path="/example",
                created_at="2026-07-28T00:00:00+00:00",
                last_opened_at="2026-07-28T00:00:00+00:00",
            ),
        ),
        workspaces=(),
    )

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        store.save_catalog(replacement)

    assert store.load_catalog() == original
    assert tuple(tmp_path.glob("*.tmp")) == ()


def test_ade_contracts_are_immutable_and_forbid_unknown_fields() -> None:
    context = AdeViewContext(
        active_project_id=None,
        active_workspace_id=None,
        active_view="projects",
    )
    with pytest.raises(ValidationError):
        AdeViewContext.model_validate(
            {
                **context.model_dump(),
                "run_status": "completed",
            }
        )
    with pytest.raises(ValidationError):
        context.active_view = "runs"
