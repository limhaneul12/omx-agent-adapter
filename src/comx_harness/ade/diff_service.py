from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from comx_harness.schemas.ade_inspection_schemas import (
    GitChangedFile,
    GitDiffProjection,
)

GitRunner = Callable[..., subprocess.CompletedProcess[bytes]]


class GitDiffService:
    """Project read-only Git status and diff evidence for the ADE."""

    def __init__(self, runner: GitRunner = subprocess.run) -> None:
        self._runner = runner

    def inspect(self, workspace: str | Path) -> GitDiffProjection:
        resolved_workspace = Path(workspace).expanduser().resolve()
        if not resolved_workspace.is_dir():
            return self._result(
                resolved_workspace,
                state="unknown",
                message="workspace directory does not exist",
            )
        try:
            status = self._git(
                resolved_workspace,
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            )
        except FileNotFoundError:
            return self._result(
                resolved_workspace,
                state="unknown",
                message="git executable is unavailable",
            )
        if status.returncode != 0:
            message = self._decode_error(status.stderr)
            if "not a git repository" in message.lower():
                return self._result(
                    resolved_workspace,
                    state="unknown",
                    message=message,
                )
            return self._result(
                resolved_workspace,
                state="error",
                message=message or f"git status exited with {status.returncode}",
            )

        staged = self._git(
            resolved_workspace,
            "diff",
            "--cached",
            "--no-ext-diff",
            "--",
        )
        unstaged = self._git(
            resolved_workspace,
            "diff",
            "--no-ext-diff",
            "--",
        )
        failed_diff = next(
            (result for result in (staged, unstaged) if result.returncode != 0),
            None,
        )
        if failed_diff is not None:
            return self._result(
                resolved_workspace,
                state="error",
                files=self._parse_status(status.stdout),
                message=self._decode_error(failed_diff.stderr)
                or f"git diff exited with {failed_diff.returncode}",
            )
        return self._result(
            resolved_workspace,
            state="available",
            files=self._parse_status(status.stdout),
            staged_diff=staged.stdout.decode("utf-8", errors="replace"),
            unstaged_diff=unstaged.stdout.decode("utf-8", errors="replace"),
        )

    def _git(
        self,
        workspace: Path,
        *arguments: str,
    ) -> subprocess.CompletedProcess[bytes]:
        return self._runner(
            ("git", "-C", str(workspace), *arguments),
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _parse_status(payload: bytes) -> tuple[GitChangedFile, ...]:
        entries = payload.split(b"\0")
        files: list[GitChangedFile] = []
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if not entry:
                continue
            text = entry.decode("utf-8", errors="replace")
            if len(text) < 4:
                continue
            staged_status = text[0] if text[0] not in {" ", "?"} else None
            unstaged_status = text[1] if text[1] not in {" ", "?"} else None
            path = text[3:]
            original_path: str | None = None
            if text[0] in {"R", "C"} and index < len(entries):
                original_path = entries[index].decode("utf-8", errors="replace")
                index += 1
            files.append(
                GitChangedFile(
                    path=path,
                    original_path=original_path,
                    staged_status=staged_status,
                    unstaged_status=unstaged_status,
                    untracked=text[:2] == "??",
                )
            )
        return tuple(files)

    @staticmethod
    def _decode_error(payload: bytes) -> str:
        return payload.decode("utf-8", errors="replace").strip()

    @staticmethod
    def _result(
        workspace: Path,
        *,
        state: Literal["available", "unknown", "error"],
        files: tuple[GitChangedFile, ...] = (),
        staged_diff: str = "",
        unstaged_diff: str = "",
        message: str | None = None,
    ) -> GitDiffProjection:
        return GitDiffProjection(
            workspace=str(workspace),
            state=state,
            files=files,
            staged_diff=staged_diff,
            unstaged_diff=unstaged_diff,
            message=message,
        )
