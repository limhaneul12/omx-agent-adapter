from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)


class SessionSearchRequest(StrictSchemaModel):
    """Represents the typed request boundary for session search."""

    query: NonEmptyString
    limit: int | None = None


class SessionSearchResultSnapshot(StrictSchemaModel):
    """Represents one normalized session-search result."""

    session_id: NonEmptyString
    timestamp: NonEmptyString
    cwd: NonEmptyString
    record_type: NonEmptyString
    line_number: int
    snippet: NonEmptyString


class SessionSearchSnapshot(StrictSchemaModel):
    """Represents the normalized result for `omx session search ... --json`."""

    query: NonEmptyString
    searched_files: int
    matched_sessions: int
    results: tuple[SessionSearchResultSnapshot, ...]
