from enum import StrEnum

from pydantic import Field

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


class CockpitStatusSourceState(StrEnum):
    """Normalized read status for a cockpit source surface."""

    OBSERVED = "observed"
    MISSING = "missing"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


class CockpitContradiction(StrictSchemaModel):
    """Represents one cross-surface state contradiction detected by cockpit."""

    category: NonEmptyString
    message: NonEmptyString


class CockpitDecisionReason(StrictSchemaModel):
    """Represents one evidence-backed reason for cockpit top-level guidance."""

    category: NonEmptyString
    detail: NonEmptyString
    source_names: tuple[NonEmptyString, ...] = ()


class CockpitStatusSourceObservation(StrictSchemaModel):
    """Represents one read-only source consulted for the cockpit snapshot."""

    name: NonEmptyString
    status: CockpitStatusSourceState
    detail: NonEmptyString
    evidence_path: NonEmptyString | None = None


class CockpitPullRequestObservation(StrictSchemaModel):
    """Represents read-only PR/review/check evidence for a cockpit snapshot."""

    provider: NonEmptyString
    branch: NonEmptyString
    status: NonEmptyString
    pull_request_number: int | None = Field(default=None, ge=1)
    mergeable_state: NonEmptyString | None = None
    review_state: NonEmptyString
    check_state: NonEmptyString
    detail: NonEmptyString
    url: NonEmptyString | None = None
    warnings: tuple[NonEmptyString, ...] = ()


class CockpitTeamWorkerObservation(StrictSchemaModel):
    """Represents one Team worker status observed by cockpit."""

    worker: NonEmptyString
    state: NonEmptyString
    updated_at: NonEmptyString


class CockpitTeamObservation(StrictSchemaModel):
    """Represents read-only Team evidence included in the cockpit."""

    team_name: NonEmptyString
    status: NonEmptyString
    phase: NonEmptyString | None = None
    task_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    worker_statuses: tuple[CockpitTeamWorkerObservation, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class CockpitLaneSnapshot(StrictSchemaModel):
    """Represents one read-only cockpit lane snapshot."""

    name: CockpitLaneName
    state: CockpitLaneState
    summary: NonEmptyString
    evidence_paths: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()
    team_observations: tuple[CockpitTeamObservation, ...] = ()
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
    discovered_teams: tuple[NonEmptyString, ...] = ()
    status_sources: tuple[CockpitStatusSourceObservation, ...] = ()
    pull_request_status: CockpitPullRequestObservation | None = None
    contradictions: tuple[CockpitContradiction, ...]
    lanes: tuple[CockpitLaneSnapshot, ...]
    warnings: tuple[NonEmptyString, ...] = ()
    safe_to_mutate: bool
    recommended_next_action: NonEmptyString
    decision_reasons: tuple[CockpitDecisionReason, ...] = ()
