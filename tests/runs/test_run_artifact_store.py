from pathlib import Path

import pytest

from omx_remote.runtime.commands.builtin_command_catalog import build_builtin_command_catalog
from omx_remote.runtime.commands.command_step_planner import build_command_execution_plan
from omx_remote.runtime.runs.run_artifact_store import (
    RunArtifactPathError,
    build_run_id,
    resolve_run_dir,
)
from omx_remote.runtime.runs.run_record_reader import (
    build_run_replay_plan,
    list_run_records,
    read_run_record,
)
from omx_remote.runtime.runs.run_record_writer import write_dry_run_record


def test_build_run_id_sanitizes_command_id() -> None:
    run_id = build_run_id("20260525T020000Z", "builtin:review-diff")

    assert run_id == "20260525T020000Z-builtin-review-diff"


def test_resolve_run_dir_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(RunArtifactPathError, match="unsafe run id"):
        resolve_run_dir(tmp_path, "../escape")


def test_write_and_read_dry_run_record(tmp_path: Path) -> None:
    recipe = build_builtin_command_catalog().find("builtin:review-diff")
    assert recipe is not None
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    record = write_dry_run_record(
        plan,
        cwd=tmp_path,
        timestamp="20260525T020000Z",
    )

    run_dir = resolve_run_dir(tmp_path, record.run_id)
    listed_records = list_run_records(tmp_path)
    replay_plan = build_run_replay_plan(tmp_path, record.run_id)

    assert record.run_id == "20260525T020000Z-review-diff"
    assert (run_dir / "run.json").exists()
    assert (run_dir / "plan.json").exists()
    assert (run_dir / "handoff.md").exists()
    assert read_run_record(tmp_path, record.run_id) == record
    assert listed_records.records[0].run_id == record.run_id
    assert replay_plan.run_id == record.run_id
    assert replay_plan.plan == plan
