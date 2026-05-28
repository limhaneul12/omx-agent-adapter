from enum import StrEnum

from pydantic import Field, field_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ComxTuiDaemonState(StrEnum):
    """Lifecycle states for the tmux-backed comx-agent TUI daemon."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNAVAILABLE = "unavailable"


class ComxTuiDaemonCommandPreview(StrictSchemaModel):
    """Represents an inspectable daemon command without executing it."""

    tmux_session: NonEmptyString
    tui_session_id: NonEmptyString
    cwd: NonEmptyString
    command: tuple[NonEmptyString, ...]
    attach_command: tuple[NonEmptyString, ...]


class ComxTuiDaemonStatusResult(StrictSchemaModel):
    """Represents current tmux-backed comx-agent TUI daemon status."""

    tmux_session: NonEmptyString
    tui_session_id: NonEmptyString
    cwd: NonEmptyString
    state: ComxTuiDaemonState
    tmux_available: bool
    running: bool
    process_id: int | None = Field(default=None, ge=1)
    attach_command: tuple[NonEmptyString, ...]
    warnings: tuple[NonEmptyString, ...] = ()


class ComxTuiDaemonActionResult(StrictSchemaModel):
    """Represents one daemon lifecycle action result."""

    action: NonEmptyString
    tmux_session: NonEmptyString
    tui_session_id: NonEmptyString
    cwd: NonEmptyString
    command: tuple[NonEmptyString, ...]
    exit_code: int
    stdout: str
    stderr: str
    state: ComxTuiDaemonState
    running: bool
    warnings: tuple[NonEmptyString, ...] = ()

    @field_validator("action")
    @classmethod
    def _validate_action(cls, value: str) -> str:
        """Validate that action labels are stable and non-ambiguous.

        Args:
            value [str]: Candidate action label.

        Returns:
            str: Validated action label.
        """
        allowed_actions: set[str] = {"start", "already_running", "stop", "missing"}
        if value not in allowed_actions:
            raise ValueError(f"unsupported daemon action: {value}")

        validated_action: str = value
        return validated_action
