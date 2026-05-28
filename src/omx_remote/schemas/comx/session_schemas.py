from enum import StrEnum

from pydantic import Field, field_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ComxTuiSessionStatus(StrEnum):
    """Lifecycle states for a persisted comx-agent TUI session."""

    ACTIVE = "active"
    CLOSED = "closed"


class ComxTuiSessionEvent(StrictSchemaModel):
    """Represents one persisted TUI session event."""

    timestamp: NonEmptyString
    kind: NonEmptyString
    text: NonEmptyString


class ComxTuiSessionRecord(StrictSchemaModel):
    """Represents one durable TUI session record."""

    session_id: NonEmptyString
    repo_root: NonEmptyString
    created_at: NonEmptyString
    updated_at: NonEmptyString
    status: ComxTuiSessionStatus
    last_prompt: NonEmptyString
    render_count: int = Field(ge=0)
    command_history: tuple[NonEmptyString, ...] = ()
    events: tuple[ComxTuiSessionEvent, ...] = ()

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str) -> str:
        """Validate that session ids are safe single path components.

        Args:
            value [str]: Candidate session id.

        Returns:
            str: Validated session id.
        """
        allowed_characters: set[str] = {"-", "_"}
        if not value[0].isalnum() or not all(
            character.isalnum() or character in allowed_characters
            for character in value
        ):
            raise ValueError(
                "session id must start with a letter or digit and use only "
                "letters, digits, '-' or '_'"
            )
        return value


class ComxTuiSessionListResult(StrictSchemaModel):
    """Represents persisted TUI sessions found for a repository."""

    sessions: tuple[ComxTuiSessionRecord, ...]
