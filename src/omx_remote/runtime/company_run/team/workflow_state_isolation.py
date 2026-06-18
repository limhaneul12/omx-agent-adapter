from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import orjson

from omx_remote.runtime.company_run.artifacts.artifact_writers import write_company_json
from omx_remote.shared.json_transport import json_object_or_none
from omx_remote.shared.utils.runtime_identity import utc_compact_timestamp


@dataclass(frozen=True)
class CompanyRunWorkflowStateIsolation:
    """Result of pre-Team workflow state isolation."""

    archive_path: Path | None
    evidence_path: Path | None
    detail: str


def isolate_completed_ultragoal_before_team(
    cwd: Path,
    company_root: Path,
) -> CompanyRunWorkflowStateIsolation:
    """Archive a completed stale Ultragoal state before live Team fanout.

    Args:
        cwd [Path]: Target repository root.
        company_root [Path]: Company-run artifact root.

    Returns:
        CompanyRunWorkflowStateIsolation: Isolation evidence and detail.
    """
    ultragoal_dir = cwd / ".omx" / "ultragoal"
    goals_path = ultragoal_dir / "goals.json"
    if not goals_path.is_file():
        no_state = CompanyRunWorkflowStateIsolation(
            archive_path=None,
            evidence_path=None,
            detail="No .omx/ultragoal goals.json state required isolation.",
        )
        return no_state
    if not _ultragoal_goals_are_completed(goals_path=goals_path):
        active_state = CompanyRunWorkflowStateIsolation(
            archive_path=None,
            evidence_path=None,
            detail=(
                ".omx/ultragoal exists but is not fully complete; live Team launch "
                "must remain blocked by native workflow-overlap protection."
            ),
        )
        return active_state

    archive_root = cwd / ".omx" / "ultragoal-archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_path = archive_root / (
        f"completed-before-company-run-team-{utc_compact_timestamp()}"
    )
    shutil.move(str(ultragoal_dir), str(archive_path))
    evidence_path = company_root / "team" / "workflow-state-isolation.json"
    write_company_json(
        path=evidence_path,
        payload={
            "isolated": True,
            "source_path": str(ultragoal_dir),
            "archive_path": str(archive_path),
            "reason": (
                "Completed .omx/ultragoal state was archived before live Team "
                "fanout so native OMX workflow-overlap protection does not treat "
                "stale completed artifacts as an active workflow."
            ),
        },
    )
    isolated_state = CompanyRunWorkflowStateIsolation(
        archive_path=archive_path,
        evidence_path=evidence_path,
        detail=f"Archived completed .omx/ultragoal state to {archive_path}.",
    )
    return isolated_state


def _ultragoal_goals_are_completed(goals_path: Path) -> bool:
    """Return whether every Ultragoal story is complete.

    Args:
        goals_path [Path]: `.omx/ultragoal/goals.json` path.

    Returns:
        bool: Whether the plan contains at least one goal and all are complete.
    """
    try:
        decoded: object = orjson.loads(goals_path.read_bytes())
    except orjson.JSONDecodeError:
        invalid_json = False
        return invalid_json
    payload = json_object_or_none(decoded)
    if payload is None:
        unsupported_payload = False
        return unsupported_payload
    raw_goals = payload.get("goals")
    if not isinstance(raw_goals, list) or len(raw_goals) == 0:
        missing_goals = False
        return missing_goals
    completed = True
    for goal in raw_goals:
        goal_payload = json_object_or_none(goal)
        if goal_payload is None or goal_payload.get("status") != "complete":
            completed = False
            break
    return completed
