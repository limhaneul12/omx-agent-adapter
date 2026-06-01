import subprocess
from collections.abc import Sequence

from omx_remote.schemas.codex_goal.runtime_schemas import (
    CodexGoalSpawnResult,
    CodexGoalSpawnStatus,
)


def _normalize_stream_text(stream_text: str | None) -> str:
    """Normalizes optional tmux subprocess stream text.

    Args:
        stream_text [str | None]: Raw stdout or stderr text from a tmux subprocess.

    Returns:
        str: Stream text, with missing streams represented as an empty string.
    """
    if stream_text is None:
        normalized_stream_text: str = ""
        return normalized_stream_text

    normalized_stream_text = stream_text
    return normalized_stream_text


def _read_process_id_from_tmux_session(session_locator: str) -> int | None:
    """Reads the pane process id for one tmux-backed Codex Goal session.

    Args:
        session_locator [str]: Tmux session name used to locate the Codex Goal pane.

    Returns:
        int | None: Pane process id when tmux reports a numeric id, otherwise `None`.
    """
    completed_process = subprocess.run(
        ["tmux", "display-message", "-p", "-t", session_locator, "#{pane_pid}"],
        text=True,
        capture_output=True,
        check=False,
    )
    process_id_text: str = _normalize_stream_text(completed_process.stdout).strip()
    if not process_id_text.isdigit():
        missing_process_id: int | None = None
        return missing_process_id

    process_id: int = int(process_id_text)
    return process_id


def spawn_codex_goal_session(
    goal_id: str,
    codex_command: Sequence[str],
    working_directory: str | None,
    slash_command_text: str,
) -> CodexGoalSpawnResult:
    """Spawns one detached tmux-backed Codex Goal session and injects `/goal` text.

    Args:
        goal_id [str]: Adapter-owned goal identifier used to derive the tmux session name.
        codex_command [Sequence[str]]: Native Codex command argv used to start the session.
        working_directory [str | None]: Optional directory where the tmux session should start.
        slash_command_text [str]: Full `/goal` slash command text to inject after spawn.

    Returns:
        CodexGoalSpawnResult: Spawn status, session locator, process id, and any tmux error text.
    """
    session_locator: str = f"comx-agent-goal-{goal_id}"
    new_session_command: list[str] = [
        "tmux",
        "new-session",
        "-d",
        "-s",
        session_locator,
    ]
    if working_directory is not None:
        new_session_command.extend(["-c", working_directory])
    new_session_command.extend(list(codex_command))

    completed_process = subprocess.run(
        new_session_command,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed_process.returncode != 0:
        launch_error_text: str = _normalize_stream_text(
            completed_process.stderr
        ).strip()
        if launch_error_text == "":
            launch_error_text = _normalize_stream_text(completed_process.stdout).strip()
        if launch_error_text == "":
            launch_error_text = "failed to start tmux-backed codex goal session"
        failed_result: CodexGoalSpawnResult = CodexGoalSpawnResult(
            session_locator=session_locator,
            process_id=None,
            spawn_status=CodexGoalSpawnStatus.FAILED,
            slash_command_written=False,
            error_text=launch_error_text,
        )
        return failed_result

    process_id: int | None = _read_process_id_from_tmux_session(session_locator)
    send_keys_process = subprocess.run(
        ["tmux", "send-keys", "-t", session_locator, slash_command_text, "Enter"],
        text=True,
        capture_output=True,
        check=False,
    )
    slash_command_written: bool = send_keys_process.returncode == 0
    send_keys_error_text: str | None = None
    if not slash_command_written:
        tmux_error_text: str = _normalize_stream_text(send_keys_process.stderr).strip()
        if tmux_error_text == "":
            tmux_error_text = _normalize_stream_text(send_keys_process.stdout).strip()
        if tmux_error_text == "":
            tmux_error_text = "tmux send-keys could not inject the /goal command"
        send_keys_error_text = tmux_error_text

    result: CodexGoalSpawnResult = CodexGoalSpawnResult(
        session_locator=session_locator,
        process_id=process_id,
        spawn_status=CodexGoalSpawnStatus.STARTED,
        slash_command_written=slash_command_written,
        error_text=send_keys_error_text,
    )
    return result


def is_codex_goal_session_active(session_locator: str) -> bool:
    """Checks whether one tmux-backed Codex Goal session is still present.

    Args:
        session_locator [str]: Tmux session name used to locate the Codex Goal session.

    Returns:
        bool: `True` when tmux still knows the session, otherwise `False`.
    """
    completed_process = subprocess.run(
        ["tmux", "has-session", "-t", session_locator],
        text=True,
        capture_output=True,
        check=False,
    )
    is_active: bool = completed_process.returncode == 0
    return is_active
