from pathlib import Path

import orjson

from omx_remote.runtime.runs.run_artifact_store import (
    resolve_run_dir,
    resolve_runs_root,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandExecutionPlan
from omx_remote.schemas.run_record_schemas import (
    RunListResult,
    RunRecord,
    RunReplayPlan,
)


def _read_json(path: Path) -> object:
    """Read a JSON artifact.

    Args:
        path [Path]: JSON artifact path.

    Returns:
        object: Parsed JSON value.
    """
    parsed_json: object = orjson.loads(path.read_bytes())
    return parsed_json


def read_run_record(cwd: str | Path, run_id: str) -> RunRecord:
    """Read one run record.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Run id to read.

    Returns:
        RunRecord: Parsed run record.
    """
    run_path: Path = resolve_run_dir(cwd, run_id) / "run.json"
    record = RunRecord.model_validate(_read_json(run_path))
    return record


def list_run_records(cwd: str | Path) -> RunListResult:
    """List run records under `.comx-agent/runs`.

    Args:
        cwd [str | Path]: Repository root.

    Returns:
        RunListResult: Records ordered by newest run id first.
    """
    runs_root: Path = resolve_runs_root(cwd)
    if not runs_root.exists():
        empty_result = RunListResult(records=())
        return empty_result

    records: list[RunRecord] = []
    for run_path in sorted(runs_root.glob("*/run.json"), reverse=True):
        record = RunRecord.model_validate(_read_json(run_path))
        records.append(record)

    result = RunListResult(records=tuple(records))
    return result


def read_run_plan(cwd: str | Path, run_id: str) -> CommandExecutionPlan:
    """Read one recorded plan.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Run id to read.

    Returns:
        CommandExecutionPlan: Recorded command execution plan.
    """
    plan_path: Path = resolve_run_dir(cwd, run_id) / "plan.json"
    plan = CommandExecutionPlan.model_validate(_read_json(plan_path))
    return plan


def read_run_handoff(cwd: str | Path, run_id: str) -> str:
    """Read one run handoff artifact.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Run id to read.

    Returns:
        str: Handoff markdown.
    """
    handoff_path: Path = resolve_run_dir(cwd, run_id) / "handoff.md"
    handoff_text: str = handoff_path.read_text(encoding="utf-8")
    return handoff_text


def build_run_replay_plan(cwd: str | Path, run_id: str) -> RunReplayPlan:
    """Build a dry-run replay plan from recorded artifacts.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Run id to replay.

    Returns:
        RunReplayPlan: Replay plan result.
    """
    replay = RunReplayPlan(run_id=run_id, plan=read_run_plan(cwd, run_id))
    return replay
