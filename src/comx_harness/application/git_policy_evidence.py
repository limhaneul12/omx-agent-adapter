from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from comx_harness.schemas.git_policy_schemas import (
    GitFileState,
    GitPolicyEvidence,
    GitSnapshot,
)

_PROTECTED_PATHS = ("tests/test_alexandria_api_probe_temp.py",)


class GitPolicyEvidenceService:
    """Capture and compare read-only Git evidence without mutating the repository."""

    def snapshot(self, workspace: str) -> GitSnapshot:
        root = Path(workspace).expanduser().resolve()
        head = self._optional(root, "rev-parse", "HEAD")
        branch = self._optional(root, "branch", "--show-current")
        remotes = tuple(self._lines(root, "remote", "-v"))
        remote_refs = tuple(
            self._lines(
                root,
                "for-each-ref",
                "--format=%(refname) %(objectname)",
                "refs/remotes",
            )
        )
        files = tuple(self._file_states(root))
        return GitSnapshot(
            workspace=str(root),
            head=head,
            branch=branch,
            remotes=remotes,
            remote_refs=remote_refs,
            files=files,
        )

    def compare(
        self,
        mission_id: str,
        before: GitSnapshot,
        after: GitSnapshot,
        *,
        expected_files: tuple[str, ...] = (),
        protected_paths: tuple[str, ...] = _PROTECTED_PATHS,
    ) -> GitPolicyEvidence:
        before_files = {item.path: item for item in before.files}
        after_files = {item.path: item for item in after.files}
        all_paths = sorted(set(before_files) | set(after_files))
        changed = tuple(
            path
            for path in all_paths
            if before_files.get(path) != after_files.get(path)
        )
        protected = tuple(path for path in changed if path in protected_paths)
        expected = set(expected_files)
        unexpected = tuple(
            path for path in changed if expected and path not in expected
        )
        unrelated_preserved = all(
            path in after_files and after_files[path] == state
            for path, state in before_files.items()
            if path not in expected
        )
        commit_created = before.head != after.head
        branch_changed = before.branch != after.branch
        remote_changed = (
            before.remotes != after.remotes or before.remote_refs != after.remote_refs
        )
        passed = not (
            commit_created
            or branch_changed
            or remote_changed
            or protected
            or unexpected
            or not unrelated_preserved
        )
        return GitPolicyEvidence(
            mission_id=mission_id,
            before=before,
            after=after,
            commit_created=commit_created,
            branch_changed=branch_changed,
            remote_changed=remote_changed,
            push_attempt_detected=False,
            push_detection_basis=(
                "Local Git snapshots cannot observe whether a push command was attempted. "
                "This field therefore remains false; remote_changed separately records "
                "remote configuration or remote-tracking ref changes."
            ),
            protected_files_changed=protected,
            changed_files=changed,
            unexpected_files=unexpected,
            unrelated_dirty_preserved=unrelated_preserved,
            passed=passed,
        )

    def _file_states(self, root: Path) -> list[GitFileState]:
        try:
            raw = self._run(root, "status", "--porcelain=v1", "-z")
        except subprocess.CalledProcessError:
            return []
        states: list[GitFileState] = []
        entries = [entry for entry in raw.split("\0") if entry]
        for entry in entries:
            status = entry[:2]
            path = entry[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            file_path = root / path
            digest = None
            if file_path.is_file():
                digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
            states.append(GitFileState(path=path, status=status, sha256=digest))
        states.sort(key=lambda item: item.path)
        return states

    def _optional(self, root: Path, *args: str) -> str | None:
        try:
            value = self._run(root, *args).strip()
        except subprocess.CalledProcessError:
            return None
        return value or None

    def _lines(self, root: Path, *args: str) -> list[str]:
        try:
            return [line for line in self._run(root, *args).splitlines() if line]
        except subprocess.CalledProcessError:
            return []

    def _run(self, root: Path, *args: str) -> str:
        completed = subprocess.run(
            ("git", *args),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout
