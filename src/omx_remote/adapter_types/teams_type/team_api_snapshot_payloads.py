"""Typed outbound payload contracts for read-only Team API snapshot calls."""

from typing_extensions import TypedDict


class TeamApiTeamNamePayload(TypedDict, closed=True):
    """Represents Team API calls that only require a team name."""

    team_name: str


class TeamApiTeamWorkerPayload(TypedDict, closed=True):
    """Represents Team API calls that require a team name and worker name."""

    team_name: str
    worker: str


type TeamApiSnapshotPayload = TeamApiTeamNamePayload | TeamApiTeamWorkerPayload
