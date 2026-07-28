from __future__ import annotations

import subprocess
from pathlib import Path

from comx_harness.ade.diff_service import GitDiffService


def _git(workspace: Path, *arguments: str) -> None:
    subprocess.run(
        ("git", "-C", str(workspace), *arguments),
        check=True,
        capture_output=True,
    )


def test_inspect_projects_staged_unstaged_and_untracked_changes(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-qm", "base")
    tracked.write_text("base\nstaged\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    tracked.write_text("base\nstaged\nunstaged\n", encoding="utf-8")
    (tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")

    projection = GitDiffService().inspect(tmp_path)

    assert projection.state == "available"
    assert projection.message is None
    assert [changed.path for changed in projection.files] == [
        "tracked.txt",
        "untracked.txt",
    ]
    tracked_change = projection.files[0]
    assert tracked_change.staged_status == "M"
    assert tracked_change.unstaged_status == "M"
    assert projection.files[1].untracked is True
    assert "+staged" in projection.staged_diff
    assert "+unstaged" in projection.unstaged_diff


def test_inspect_reports_unknown_for_non_repository(tmp_path: Path) -> None:
    projection = GitDiffService().inspect(tmp_path)

    assert projection.state == "unknown"
    assert projection.files == ()
    assert projection.message is not None
    assert "not a git repository" in projection.message.lower()


def test_inspect_preserves_rename_source_and_destination(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")
    (tmp_path / "old.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "old.txt")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "mv", "old.txt", "new.txt")

    projection = GitDiffService().inspect(tmp_path)

    assert len(projection.files) == 1
    assert projection.files[0].path == "new.txt"
    assert projection.files[0].original_path == "old.txt"


def test_inspect_reports_command_error_honestly(tmp_path: Path) -> None:
    def failed_runner(
        argv: tuple[str, ...],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        return subprocess.CompletedProcess(argv, 128, b"", b"fatal: broken index\n")

    projection = GitDiffService(runner=failed_runner).inspect(tmp_path)

    assert projection.state == "error"
    assert projection.message == "fatal: broken index"
