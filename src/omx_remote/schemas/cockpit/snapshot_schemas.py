from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class CockpitLaneName(StrEnum):
    """Top-level operating lanes surfaced by the agent-remote cockpit."""

    GOAL_ONLY = "goal_only"
    GOAL_RALPH = "goal_to_ralph"
    GOAL_RALPH_TEAMS = "goal_to_ralph_to_teams"
    ULTRAWORK_ONLY = "ultrawork_only"
    HYPERGOAL = "hypergoal"
    RALPH_TEAM = "ralph_to_team"


class CockpitLaneState(StrEnum):
    """Normalized cockpit state markers for operating-lane summaries."""

    MISSING = "missing"
    ACTIVE = "active"
    ENDED = "ended"
    AWAITING_RALPH = "awaiting_ralph"
    RALPH_STARTED = "ralph_started"
    NEEDS_TEAM_NAME = "needs_team_name"
    CLEAN = "clean"
    RESUMABLE = "resumable"
    STALE = "stale"
    TERMINAL = "terminal"
    INVALID = "invalid"
    PLANNED_ONLY = "planned_only"
    UNKNOWN = "unknown"


class CockpitContradiction(StrictSchemaModel):
    """Represents one cross-surface state contradiction detected by cockpit."""

    category: NonEmptyString
    message: NonEmptyString


class CockpitLaneSnapshot(StrictSchemaModel):
    """Represents one read-only cockpit lane snapshot."""

    name: CockpitLaneName
    state: CockpitLaneState
    summary: NonEmptyString
    evidence_paths: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()
    recommended_next_action: NonEmptyString


class CockpitSnapshotRequest(StrictSchemaModel):
    """Represents the typed request boundary for cockpit reads."""

    repo_root: NonEmptyString
    team_names: tuple[NonEmptyString, ...] = ()


class CockpitSnapshot(StrictSchemaModel):
    """Represents a repo-scoped read-only cockpit snapshot."""

    repo_root: NonEmptyString
    runtime_summary: str
    active_runtime_modes: tuple[NonEmptyString, ...]
    contradictions: tuple[CockpitContradiction, ...]
    lanes: tuple[CockpitLaneSnapshot, ...]
    safe_to_mutate: bool
    recommended_next_action: NonEmptyString
