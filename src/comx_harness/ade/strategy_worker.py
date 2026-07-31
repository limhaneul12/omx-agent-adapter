from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from comx_harness.application.strategy_service import StrategyService
from comx_harness.schemas.strategy_schemas import (
    StrategyDefinition,
    StrategyLaunchRecord,
)
from comx_harness.storage.json_file_store import read_json
from comx_harness.storage.time_identity import utc_timestamp
from comx_harness.storage.workspace_layout import WorkspaceLayout

from .detached_operations import write_private_operation_model


def execute_strategy(
    workspace: str | Path,
    strategy_id: str,
    *,
    service: StrategyService | None = None,
) -> StrategyLaunchRecord:
    layout = WorkspaceLayout.from_workspace(workspace)
    paths = layout.strategy_paths(strategy_id)
    definition = StrategyDefinition.model_validate(read_json(paths.request))
    launch = _wait_for_launch_record(paths.launch)
    active_service = service or StrategyService()
    try:
        result = active_service.execute(definition)
        write_private_operation_model(paths.result, result)
    except Exception as error:
        failed = launch.model_copy(
            update={
                "status": "failed",
                "finished_at": utc_timestamp(),
                "error_message": f"{type(error).__name__}: {error}",
            }
        )
        write_private_operation_model(paths.launch, failed)
        raise
    succeeded = launch.model_copy(
        update={"status": "succeeded", "finished_at": utc_timestamp()}
    )
    write_private_operation_model(paths.launch, succeeded)
    return succeeded


def _wait_for_launch_record(path: Path) -> StrategyLaunchRecord:
    deadline = time.monotonic() + 5.0
    while True:
        record = StrategyLaunchRecord.model_validate(read_json(path))
        if record.pid is not None:
            return record
        if time.monotonic() >= deadline:
            raise RuntimeError("strategy launch metadata was not persisted")
        time.sleep(0.01)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--strategy-id", required=True)
    arguments = parser.parse_args()
    try:
        execute_strategy(arguments.workspace, arguments.strategy_id)
    except Exception as error:
        print(f"detached strategy failed: {type(error).__name__}: {error}")
        return 1
    print(f"detached strategy completed by pid {os.getpid()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
