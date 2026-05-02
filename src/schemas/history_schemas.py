from pydantic import BaseModel, ConfigDict, Field

from schemas.common_schemas import NonEmptyString


class SessionSearchRequest(BaseModel):
    """Represents the typed request boundary for session search."""

    model_config = ConfigDict(extra="forbid")

    query: NonEmptyString
    limit: int | None = None


class SessionSearchResultSnapshot(BaseModel):
    """Represents one normalized session-search result."""

    model_config = ConfigDict(extra="forbid")

    session_id: NonEmptyString
    timestamp: NonEmptyString
    cwd: NonEmptyString
    record_type: NonEmptyString
    line_number: int
    snippet: NonEmptyString


class SessionSearchSnapshot(BaseModel):
    """Represents the normalized result for `omx session search ... --json`."""

    model_config = ConfigDict(extra="forbid")

    query: NonEmptyString
    searched_files: int
    matched_sessions: int
    results: list[SessionSearchResultSnapshot] = Field(default_factory=list)
