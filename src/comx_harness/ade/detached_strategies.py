from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from comx_harness.schemas.strategy_schemas import (
    StrategyDefinition,
    StrategyLaunchRecord,
)
from comx_harness.storage.json_file_store import read_json
from comx_harness.storage.time_identity import utc_timestamp
from comx_harness.storage.workspace_layout import WorkspaceLayout

from .detached_operations import write_private_operation_model

StrategyLauncher = Callable[..., subprocess.Popen[bytes]]


class DetachedStrategyService:
    """Launch one durable Strategy aggregate outside the caller process."""

    def __init__(
        self,
        *,
        launcher: StrategyLauncher = subprocess.Popen,
        python_executable: str = sys.executable,
    ) -> None:
        self._launcher = launcher
        self._python_executable = python_executable

    def start(self, definition: StrategyDefinition) -> StrategyLaunchRecord:
        workspace = Path(definition.stages[0].workspace).expanduser().resolve()
        paths = WorkspaceLayout.from_workspace(workspace).strategy_paths(
            definition.strategy_id
        )
        if paths.launch.exists():
            existing = StrategyLaunchRecord.model_validate(read_json(paths.launch))
            existing_definition = StrategyDefinition.model_validate(
                read_json(paths.request)
            )
            if existing_definition != definition:
                raise ValueError(
                    f"strategy_id {definition.strategy_id!r} already has another definition"
                )
            return existing

        paths.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_private_operation_model(paths.request, definition)
        queued = StrategyLaunchRecord(
            strategy_id=definition.strategy_id,
            workspace=str(workspace),
            status="queued",
            created_at=utc_timestamp(),
            request_path=str(paths.request),
            result_path=str(paths.result),
            stdout_path=str(paths.stdout),
            stderr_path=str(paths.stderr),
        )
        write_private_operation_model(paths.launch, queued)
        paths.stdout.touch(mode=0o600, exist_ok=False)
        paths.stderr.touch(mode=0o600, exist_ok=False)
        try:
            with paths.stdout.open("ab") as stdout, paths.stderr.open("ab") as stderr:
                process = self._launcher(
                    (
                        self._python_executable,
                        "-m",
                        "comx_harness.ade.strategy_worker",
                        "--workspace",
                        str(workspace),
                        "--strategy-id",
                        definition.strategy_id,
                    ),
                    cwd=str(workspace),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                    close_fds=True,
                )
        except OSError as error:
            failed = queued.model_copy(
                update={
                    "status": "failed",
                    "finished_at": utc_timestamp(),
                    "error_message": f"{type(error).__name__}: {error}",
                }
            )
            write_private_operation_model(paths.launch, failed)
            return failed
        running = queued.model_copy(
            update={
                "status": "running",
                "started_at": utc_timestamp(),
                "pid": process.pid,
            }
        )
        write_private_operation_model(paths.launch, running)
        return running

    def read(self, workspace: str, strategy_id: str) -> StrategyLaunchRecord:
        paths = WorkspaceLayout.from_workspace(workspace).strategy_paths(strategy_id)
        return StrategyLaunchRecord.model_validate(read_json(paths.launch))
