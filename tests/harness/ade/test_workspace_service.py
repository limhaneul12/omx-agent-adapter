from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from comx_harness.ade.state_store import AdeStateStore
from comx_harness.ade.workspace_service import WorkspaceService
from comx_harness.schemas.ade_schemas import AdeStateSettings


def _git(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(path), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "tests@example.com")
    _git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    return path


def _service(tmp_path: Path) -> WorkspaceService:
    state_root = tmp_path / "state"
    return WorkspaceService(AdeStateStore(AdeStateSettings(state_root=state_root)))


def test_register_reopen_and_adopt_use_canonical_path_identity(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    service = _service(tmp_path)

    project = service.register_project(repository)
    duplicate = service.register_project(repository / ".")
    reopened = service.reopen_project(project.project_id)
    workspace = service.adopt_workspace(project.project_id, repository)
    duplicate_workspace = service.adopt_workspace(
        project.project_id,
        repository / ".",
    )

    assert duplicate.project_id == project.project_id
    assert reopened.project_id == project.project_id
    assert reopened.last_opened_at >= project.last_opened_at
    assert duplicate_workspace.workspace_id == workspace.workspace_id
    assert workspace.root_path == str(repository.resolve())


def test_discovers_existing_git_worktrees_and_reports_live_state(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    existing_worktree = tmp_path / "existing worktree"
    _git(repository, "worktree", "add", "-b", "existing", str(existing_worktree))
    service = _service(tmp_path)
    project = service.register_project(repository)

    discovered = service.discover_worktrees(project.project_id)

    assert {Path(item.root_path) for item in discovered} == {
        repository.resolve(),
        existing_worktree.resolve(),
    }
    worktree = next(
        item for item in discovered if Path(item.root_path) == existing_worktree
    )
    clean_status = service.inspect_workspace(worktree.workspace_id)
    assert clean_status.branch == "existing"
    assert clean_status.dirty is False
    assert clean_status.missing is False
    assert clean_status.git_repository is True

    (existing_worktree / "change.txt").write_text("dirty\n", encoding="utf-8")
    assert service.inspect_workspace(worktree.workspace_id).dirty is True


def test_adopts_existing_worktree_outside_project_directory(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    existing_worktree = tmp_path / "external-worktree"
    _git(repository, "worktree", "add", "-b", "external", str(existing_worktree))
    service = _service(tmp_path)
    project = service.register_project(repository)

    adopted = service.adopt_workspace(project.project_id, existing_worktree)

    assert adopted.root_path == str(existing_worktree.resolve())
    assert adopted.kind == "adopted_directory"


def test_creates_managed_worktree_under_state_root_without_committing_or_pushing(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    service = _service(tmp_path)
    project = service.register_project(repository)
    original_head = _git(repository, "rev-parse", "HEAD").stdout.strip()

    workspace = service.create_managed_worktree(
        project.project_id,
        branch="feature/isolated",
    )

    workspace_path = Path(workspace.root_path)
    assert workspace.kind == "managed_worktree"
    assert workspace_path.is_relative_to(tmp_path / "state" / "worktrees")
    assert workspace_path.is_dir()
    assert _git(workspace_path, "branch", "--show-current").stdout.strip() == (
        "feature/isolated"
    )
    assert _git(workspace_path, "rev-parse", "HEAD").stdout.strip() == original_head
    assert _git(repository, "rev-list", "--count", "HEAD").stdout.strip() == "1"


def test_missing_workspace_is_reported_without_fabricated_git_state(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    service = _service(tmp_path)
    project = service.register_project(repository)
    workspace = service.adopt_workspace(project.project_id, repository)
    subprocess.run(
        ("rm", "-rf", workspace.root_path),
        check=True,
        capture_output=True,
        text=True,
    )

    status = service.inspect_workspace(workspace.workspace_id)

    assert status.missing is True
    assert status.git_repository is False
    assert status.branch is None
    assert status.dirty is None


def test_adoption_rejects_unrelated_directory(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    service = _service(tmp_path)
    project = service.register_project(repository)

    with pytest.raises(ValueError, match="outside"):
        service.adopt_workspace(project.project_id, unrelated)
