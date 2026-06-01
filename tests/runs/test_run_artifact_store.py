import sys
from pathlib import Path

import pytest

from omx_remote.runtime.commands.catalog.builtin_command_catalog import (
    build_builtin_command_catalog,
)
from omx_remote.runtime.commands.planning.command_step_planner import (
    build_command_execution_plan,
)
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
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)


def _repo_recipe(command_id: str, steps: tuple[CommandStep, ...]) -> CommandRecipe:
    recipe = CommandRecipe(
        id=command_id,
        source=CommandSource.REPO,
        description=f"Dry-run {command_id}.",
        steps=steps,
    )
    return recipe


def test_build_run_id_sanitizes_command_id() -> None:
    run_id = build_run_id("20260525T020000Z", "builtin:review-gate")

    assert run_id == "20260525T020000Z-builtin-review-gate"


def test_resolve_run_dir_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(RunArtifactPathError, match="unsafe run id"):
        resolve_run_dir(tmp_path, "../escape")


def test_write_and_read_dry_run_record(tmp_path: Path) -> None:
    recipe = build_builtin_command_catalog().find("builtin:review-gate")
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

    assert record.run_id == "20260525T020000Z-review-gate"
    assert (run_dir / "run.json").exists()
    assert (run_dir / "plan.json").exists()
    assert (run_dir / "handoff.md").exists()
    assert read_run_record(tmp_path, record.run_id) == record
    assert listed_records.records[0].run_id == record.run_id
    assert replay_plan.run_id == record.run_id
    assert replay_plan.plan == plan


def test_dry_run_record_collision_gets_unique_suffix(tmp_path: Path) -> None:
    recipe = build_builtin_command_catalog().find("builtin:review-gate")
    assert recipe is not None
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    first = write_dry_run_record(
        plan,
        cwd=tmp_path,
        timestamp="20260525T020100Z",
    )
    second = write_dry_run_record(
        plan,
        cwd=tmp_path,
        timestamp="20260525T020100Z",
    )

    assert first.run_id == "20260525T020100Z-review-gate"
    assert second.run_id == "20260525T020100Z-review-gate-02"
    assert resolve_run_dir(tmp_path, first.run_id).exists()
    assert resolve_run_dir(tmp_path, second.run_id).exists()


def test_dry_run_record_redacts_secret_argv_in_artifacts(tmp_path: Path) -> None:
    recipe = _repo_recipe(
        "dry-redact",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(
                    sys.executable,
                    "-c",
                    "print('token=script unquoted tail')",
                    "--token",
                    "argv spaced tail",
                    "--key=key spaced tail",
                ),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    record = write_dry_run_record(
        plan,
        cwd=tmp_path,
        timestamp="20260525T020200Z",
    )

    run_dir = resolve_run_dir(tmp_path, record.run_id)
    persisted_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in run_dir.rglob("*")
        if path.is_file()
    )
    assert "argv spaced tail" not in persisted_text
    assert "key spaced tail" not in persisted_text
    assert "script unquoted tail" not in persisted_text
    assert "unquoted tail" not in persisted_text
    assert "spaced tail" not in persisted_text
    assert "argv spaced tail" not in " ".join(record.native_commands[0].argv)
