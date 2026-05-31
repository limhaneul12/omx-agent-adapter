from pathlib import Path
from typing import Final

import orjson

from omx_remote.schemas.comx.session_schemas import (
    ComxTuiSessionEvent,
    ComxTuiSessionListResult,
    ComxTuiSessionRecord,
    ComxTuiSessionStatus,
)
from omx_remote.shared.utils.runtime_identity import utcnow_text
from omx_remote.shared.utils.session_identifiers import validate_session_identifier

COMX_SESSION_ROOT: Final[str] = ".comx-agent/sessions"


class ComxTuiSessionPathError(ValueError):
    """Raised when a comx-agent TUI session path is unsafe."""


def resolve_session_root(cwd: str | Path) -> Path:
    """Resolve the session storage root for one repository.

    Args:
        cwd [str | Path]: Repository root.

    Returns:
        Path: `.comx-agent/sessions` path.
    """
    root_path: Path = Path(cwd).resolve()
    session_root: Path = root_path / COMX_SESSION_ROOT
    return session_root


def _validate_session_id(session_id: str) -> None:
    """Validate a session id before using it as a path segment.

    Args:
        session_id [str]: Candidate session id.
    """
    try:
        validate_session_identifier(session_id)
    except ValueError as error:
        raise ComxTuiSessionPathError(f"unsafe session id: {session_id}") from error


def resolve_session_path(cwd: str | Path, session_id: str) -> Path:
    """Resolve one session file and reject path traversal.

    Args:
        cwd [str | Path]: Repository root.
        session_id [str]: Safe session id.

    Returns:
        Path: Session JSON path.
    """
    _validate_session_id(session_id)
    session_root: Path = resolve_session_root(cwd)
    session_path: Path = (session_root / f"{session_id}.json").resolve()
    if session_root not in session_path.parents:
        raise ComxTuiSessionPathError(f"unsafe session id: {session_id}")
    return session_path


def read_tui_session(cwd: str | Path, session_id: str) -> ComxTuiSessionRecord | None:
    """Read one persisted TUI session when it exists.

    Args:
        cwd [str | Path]: Repository root.
        session_id [str]: Session id to read.

    Returns:
        ComxTuiSessionRecord | None: Session record when present.
    """
    session_path: Path = resolve_session_path(cwd, session_id)
    if not session_path.exists():
        missing_session: None = None
        return missing_session

    payload: object = orjson.loads(session_path.read_bytes())
    session = ComxTuiSessionRecord.model_validate(payload)
    return session


def _write_tui_session(cwd: str | Path, session: ComxTuiSessionRecord) -> Path:
    """Persist one TUI session record.

    Args:
        cwd [str | Path]: Repository root.
        session [ComxTuiSessionRecord]: Session record to write.

    Returns:
        Path: Written session path.
    """
    session_path: Path = resolve_session_path(cwd, session.session_id)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_bytes(
        orjson.dumps(session.model_dump(mode="json"), option=orjson.OPT_INDENT_2)
    )
    return session_path


def start_or_resume_tui_session(
    cwd: str | Path,
    session_id: str,
    prompt: str,
) -> ComxTuiSessionRecord:
    """Start a new TUI session or resume an existing one.

    Args:
        cwd [str | Path]: Repository root.
        session_id [str]: Session id.
        prompt [str]: Current prompt text.

    Returns:
        ComxTuiSessionRecord: Active session record.
    """
    existing_session: ComxTuiSessionRecord | None = read_tui_session(cwd, session_id)
    now: str = utcnow_text()
    if existing_session is None:
        started_event = ComxTuiSessionEvent(
            timestamp=now,
            kind="started",
            text=f"Session {session_id} started.",
        )
        session = ComxTuiSessionRecord(
            session_id=session_id,
            repo_root=str(Path(cwd).resolve()),
            created_at=now,
            updated_at=now,
            status=ComxTuiSessionStatus.ACTIVE,
            last_prompt=prompt,
            render_count=0,
            events=(started_event,),
        )
    else:
        resumed_event = ComxTuiSessionEvent(
            timestamp=now,
            kind="resumed",
            text=f"Session {session_id} resumed.",
        )
        session = existing_session.model_copy(
            update={
                "updated_at": now,
                "status": ComxTuiSessionStatus.ACTIVE,
                "last_prompt": prompt,
                "events": (*existing_session.events, resumed_event),
            }
        )

    _write_tui_session(cwd, session)
    return session


def record_tui_render(
    cwd: str | Path,
    session: ComxTuiSessionRecord,
    prompt: str,
) -> ComxTuiSessionRecord:
    """Record that a TUI frame was rendered.

    Args:
        cwd [str | Path]: Repository root.
        session [ComxTuiSessionRecord]: Session to update.
        prompt [str]: Prompt rendered in the frame.

    Returns:
        ComxTuiSessionRecord: Updated session.
    """
    now: str = utcnow_text()
    render_event = ComxTuiSessionEvent(
        timestamp=now,
        kind="rendered",
        text=prompt,
    )
    updated_session = session.model_copy(
        update={
            "updated_at": now,
            "status": ComxTuiSessionStatus.ACTIVE,
            "last_prompt": prompt,
            "render_count": session.render_count + 1,
            "events": (*session.events, render_event),
        }
    )
    _write_tui_session(cwd, updated_session)
    return updated_session


def record_tui_command(
    cwd: str | Path,
    session: ComxTuiSessionRecord,
    command_text: str,
) -> ComxTuiSessionRecord:
    """Record one interactive slash command.

    Args:
        cwd [str | Path]: Repository root.
        session [ComxTuiSessionRecord]: Session to update.
        command_text [str]: Command entered by the user.

    Returns:
        ComxTuiSessionRecord: Updated session.
    """
    now: str = utcnow_text()
    command_event = ComxTuiSessionEvent(
        timestamp=now,
        kind="command",
        text=command_text,
    )
    updated_session = session.model_copy(
        update={
            "updated_at": now,
            "status": ComxTuiSessionStatus.ACTIVE,
            "command_history": (*session.command_history, command_text),
            "events": (*session.events, command_event),
        }
    )
    _write_tui_session(cwd, updated_session)
    return updated_session


def close_tui_session(
    cwd: str | Path,
    session: ComxTuiSessionRecord,
    reason: str,
) -> ComxTuiSessionRecord:
    """Mark a TUI session closed and persist it.

    Args:
        cwd [str | Path]: Repository root.
        session [ComxTuiSessionRecord]: Session to close.
        reason [str]: Close reason.

    Returns:
        ComxTuiSessionRecord: Closed session.
    """
    now: str = utcnow_text()
    closed_event = ComxTuiSessionEvent(
        timestamp=now,
        kind="closed",
        text=reason,
    )
    closed_session = session.model_copy(
        update={
            "updated_at": now,
            "status": ComxTuiSessionStatus.CLOSED,
            "events": (*session.events, closed_event),
        }
    )
    _write_tui_session(cwd, closed_session)
    return closed_session


def list_tui_sessions(cwd: str | Path) -> ComxTuiSessionListResult:
    """List persisted TUI sessions for one repository.

    Args:
        cwd [str | Path]: Repository root.

    Returns:
        ComxTuiSessionListResult: Sessions ordered newest-first by update time.
    """
    session_root: Path = resolve_session_root(cwd)
    if not session_root.exists():
        empty_result = ComxTuiSessionListResult(sessions=())
        return empty_result

    sessions: list[ComxTuiSessionRecord] = []
    for session_path in sorted(session_root.glob("*.json")):
        payload: object = orjson.loads(session_path.read_bytes())
        session = ComxTuiSessionRecord.model_validate(payload)
        sessions.append(session)

    sorted_sessions: tuple[ComxTuiSessionRecord, ...] = tuple(
        sorted(sessions, key=lambda session: session.updated_at, reverse=True)
    )
    result = ComxTuiSessionListResult(sessions=sorted_sessions)
    return result
