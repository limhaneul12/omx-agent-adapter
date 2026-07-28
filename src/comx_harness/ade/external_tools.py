from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from comx_harness.schemas.ade_inspection_schemas import (
    ExternalToolLaunch,
    ExternalToolTarget,
)

ExternalLauncher = Callable[..., subprocess.Popen[bytes]]
ExternalToolKind = Literal["finder", "editor", "terminal", "tmux"]


class ExternalToolService:
    """Resolve and launch inspectable external-tool argv without a shell."""

    def __init__(
        self,
        *,
        platform: str = sys.platform,
        launcher: ExternalLauncher = subprocess.Popen,
    ) -> None:
        self._platform = platform
        self._launcher = launcher

    def finder_target(self, target: str | Path) -> ExternalToolTarget:
        path = self._existing_path(target)
        if path is None:
            return self._unsupported("finder", "target path does not exist")
        if self._platform != "darwin":
            return self._unsupported(
                "finder",
                f"Finder is unsupported on platform {self._platform}",
            )
        argv = ("open", "-R", str(path)) if path.is_file() else ("open", str(path))
        return self._target("finder", argv, f"resolved existing path {path}")

    def editor_target(
        self,
        target: str | Path,
        *,
        application: str,
    ) -> ExternalToolTarget:
        path = self._existing_path(target)
        if path is None:
            return self._unsupported("editor", "target path does not exist")
        if self._platform != "darwin":
            return self._unsupported(
                "editor",
                f"external editor launch is unsupported on platform {self._platform}",
            )
        if not application.strip() or self._has_control_character(application):
            return self._unsupported("editor", "editor application name is invalid")
        return self._target(
            "editor",
            ("open", "-a", application, str(path)),
            f"operator selected editor {application!r} for {path}",
        )

    def terminal_target(self, target: str | Path) -> ExternalToolTarget:
        path = self._existing_path(target)
        if path is None:
            return self._unsupported("terminal", "target path does not exist")
        directory = path if path.is_dir() else path.parent
        if self._platform != "darwin":
            return self._unsupported(
                "terminal",
                f"Terminal launch is unsupported on platform {self._platform}",
            )
        return self._target(
            "terminal",
            ("open", "-a", "Terminal", str(directory)),
            f"resolved existing directory {directory}",
        )

    def tmux_attach_target(self, session_id: str | None) -> ExternalToolTarget:
        if session_id is None or not session_id.strip():
            return self._unsupported(
                "tmux",
                "tmux attach requires an explicit observed session identity",
            )
        if self._has_control_character(session_id):
            return self._unsupported("tmux", "tmux session identity is invalid")
        return self._target(
            "tmux",
            ("tmux", "attach-session", "-t", session_id),
            f"using explicit observed tmux session identity {session_id!r}",
        )

    def launch(self, target: ExternalToolTarget) -> ExternalToolLaunch:
        if not target.supported or not target.argv:
            return ExternalToolLaunch(
                target=target,
                message=target.message or "external target is unsupported",
            )
        try:
            process = self._launcher(
                target.argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as error:
            return ExternalToolLaunch(target=target, message=str(error))
        return ExternalToolLaunch(target=target, pid=process.pid, launched=True)

    @staticmethod
    def _existing_path(target: str | Path) -> Path | None:
        path = Path(target).expanduser().resolve()
        return path if path.exists() else None

    @staticmethod
    def _has_control_character(value: str) -> bool:
        return any(character in value for character in ("\0", "\n", "\r"))

    @staticmethod
    def _target(
        kind: ExternalToolKind,
        argv: Sequence[str],
        evidence: str,
    ) -> ExternalToolTarget:
        return ExternalToolTarget(
            kind=kind,
            supported=True,
            argv=tuple(argv),
            evidence=evidence,
        )

    @staticmethod
    def _unsupported(
        kind: ExternalToolKind,
        message: str,
    ) -> ExternalToolTarget:
        return ExternalToolTarget(
            kind=kind,
            supported=False,
            evidence="no launch argv resolved",
            message=message,
        )
