import shlex
import subprocess
from pathlib import Path
from shutil import which

from omx_remote.runtime.comx.tui_session_store import resolve_session_path
from omx_remote.schemas.comx.tui_daemon_schemas import (
    ComxTuiDaemonActionResult,
    ComxTuiDaemonCommandPreview,
    ComxTuiDaemonState,
    ComxTuiDaemonStatusResult,
)


def normalize_daemon_session_id(session_id: str) -> str:
    """Normalize and validate a durable TUI session id for daemon use.

    Args:
        session_id [str]: Candidate TUI session id.

    Returns:
        str: Validated TUI session id.
    """
    normalized_session_id: str = session_id.strip()
    resolve_session_path(Path.cwd(), normalized_session_id)
    return normalized_session_id


def build_daemon_tmux_session_name(session_id: str) -> str:
    """Build the tmux session name for one durable TUI session.

    Args:
        session_id [str]: Durable TUI session id.

    Returns:
        str: Tmux session name.
    """
    normalized_session_id: str = normalize_daemon_session_id(session_id)
    tmux_session: str = f"comx-agent-{normalized_session_id}"
    return tmux_session


def build_daemon_tui_argv(
    cwd: str | Path,
    session_id: str,
    executable: str = "comx-agent",
) -> tuple[str, ...]:
    """Build the comx-agent TUI argv used inside tmux.

    Args:
        cwd [str | Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        executable [str]: comx-agent executable path or name.

    Returns:
        tuple[str, ...]: TUI argv.
    """
    normalized_session_id: str = normalize_daemon_session_id(session_id)
    resolved_cwd: str = str(Path(cwd).resolve())
    argv: tuple[str, ...] = (
        executable,
        "tui",
        "--cwd",
        resolved_cwd,
        "--session-id",
        normalized_session_id,
    )
    return argv


def build_daemon_start_command(
    cwd: str | Path,
    session_id: str,
    executable: str = "comx-agent",
    tmux_session: str | None = None,
) -> ComxTuiDaemonCommandPreview:
    """Build the detached tmux command for the comx-agent TUI daemon.

    Args:
        cwd [str | Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        executable [str]: comx-agent executable path or name.
        tmux_session [str | None]: Optional tmux session name override.

    Returns:
        ComxTuiDaemonCommandPreview: Inspectable daemon command preview.
    """
    normalized_session_id: str = normalize_daemon_session_id(session_id)
    resolved_cwd: str = str(Path(cwd).resolve())
    resolved_tmux_session: str = tmux_session or build_daemon_tmux_session_name(
        normalized_session_id
    )
    tui_argv: tuple[str, ...] = build_daemon_tui_argv(
        resolved_cwd,
        normalized_session_id,
        executable=executable,
    )
    command: tuple[str, ...] = (
        "tmux",
        "new-session",
        "-d",
        "-s",
        resolved_tmux_session,
        "-c",
        resolved_cwd,
        shlex.join(tui_argv),
    )
    attach_command: tuple[str, ...] = (
        "tmux",
        "attach-session",
        "-t",
        resolved_tmux_session,
    )
    preview = ComxTuiDaemonCommandPreview(
        tmux_session=resolved_tmux_session,
        tui_session_id=normalized_session_id,
        cwd=resolved_cwd,
        command=command,
        attach_command=attach_command,
    )
    return preview


def _stream_text(stream_text: str | None) -> str:
    """Normalize optional subprocess stream text.

    Args:
        stream_text [str | None]: Raw stdout or stderr text.

    Returns:
        str: Stream text with missing streams represented as empty.
    """
    normalized_text: str = stream_text or ""
    return normalized_text


def _tmux_available() -> bool:
    """Check whether tmux is available on PATH.

    Returns:
        bool: True when tmux is available.
    """
    available: bool = which("tmux") is not None
    return available


def _tmux_has_session(tmux_session: str) -> bool:
    """Check whether tmux knows one session.

    Args:
        tmux_session [str]: Tmux session name.

    Returns:
        bool: True when session exists.
    """
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        ("tmux", "has-session", "-t", tmux_session),
        text=True,
        capture_output=True,
        check=False,
    )
    exists: bool = completed_process.returncode == 0
    return exists


def _read_tmux_process_id(tmux_session: str) -> int | None:
    """Read the pane process id for one tmux session.

    Args:
        tmux_session [str]: Tmux session name.

    Returns:
        int | None: Process id when tmux reports a numeric value.
    """
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        ("tmux", "display-message", "-p", "-t", tmux_session, "#{pane_pid}"),
        text=True,
        capture_output=True,
        check=False,
    )
    process_id_text: str = _stream_text(completed_process.stdout).strip()
    if not process_id_text.isdigit():
        missing_process_id: int | None = None
        return missing_process_id

    process_id: int = int(process_id_text)
    return process_id


def read_comx_tui_daemon_status(
    cwd: str | Path,
    session_id: str,
    tmux_session: str | None = None,
) -> ComxTuiDaemonStatusResult:
    """Read tmux-backed comx-agent TUI daemon status.

    Args:
        cwd [str | Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session name override.

    Returns:
        ComxTuiDaemonStatusResult: Daemon status.
    """
    preview: ComxTuiDaemonCommandPreview = build_daemon_start_command(
        cwd,
        session_id,
        tmux_session=tmux_session,
    )
    warnings: list[str] = []
    tmux_available: bool = _tmux_available()
    running: bool = False
    process_id: int | None = None
    state: ComxTuiDaemonState = ComxTuiDaemonState.STOPPED
    if not tmux_available:
        state = ComxTuiDaemonState.UNAVAILABLE
        warnings.append("tmux was not detected; install tmux for daemon mode.")
    else:
        running = _tmux_has_session(preview.tmux_session)
        if running:
            process_id = _read_tmux_process_id(preview.tmux_session)
            state = ComxTuiDaemonState.RUNNING

    status = ComxTuiDaemonStatusResult(
        tmux_session=preview.tmux_session,
        tui_session_id=preview.tui_session_id,
        cwd=preview.cwd,
        state=state,
        tmux_available=tmux_available,
        running=running,
        process_id=process_id,
        attach_command=preview.attach_command,
        warnings=tuple(warnings),
    )
    return status


def start_comx_tui_daemon(
    cwd: str | Path,
    session_id: str,
    executable: str = "comx-agent",
    tmux_session: str | None = None,
    force: bool = False,
) -> ComxTuiDaemonActionResult:
    """Start the detached tmux-backed comx-agent TUI daemon.

    Args:
        cwd [str | Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        executable [str]: comx-agent executable path or name.
        tmux_session [str | None]: Optional tmux session name override.
        force [bool]: Whether to kill an existing session before start.

    Returns:
        ComxTuiDaemonActionResult: Start action result.
    """
    preview: ComxTuiDaemonCommandPreview = build_daemon_start_command(
        cwd,
        session_id,
        executable=executable,
        tmux_session=tmux_session,
    )
    if not _tmux_available():
        missing_result = ComxTuiDaemonActionResult(
            action="missing",
            tmux_session=preview.tmux_session,
            tui_session_id=preview.tui_session_id,
            cwd=preview.cwd,
            command=preview.command,
            exit_code=127,
            stdout="",
            stderr="tmux was not detected; install tmux for daemon mode.",
            state=ComxTuiDaemonState.UNAVAILABLE,
            running=False,
            warnings=("tmux was not detected; install tmux for daemon mode.",),
        )
        return missing_result

    already_running: bool = _tmux_has_session(preview.tmux_session)
    if already_running and not force:
        already_running_result = ComxTuiDaemonActionResult(
            action="already_running",
            tmux_session=preview.tmux_session,
            tui_session_id=preview.tui_session_id,
            cwd=preview.cwd,
            command=preview.attach_command,
            exit_code=0,
            stdout="",
            stderr="",
            state=ComxTuiDaemonState.RUNNING,
            running=True,
            warnings=("daemon session is already running.",),
        )
        return already_running_result

    if already_running and force:
        subprocess.run(
            ("tmux", "kill-session", "-t", preview.tmux_session),
            text=True,
            capture_output=True,
            check=False,
        )

    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        preview.command,
        text=True,
        capture_output=True,
        check=False,
    )
    running: bool = completed_process.returncode == 0 and _tmux_has_session(
        preview.tmux_session
    )
    state: ComxTuiDaemonState = (
        ComxTuiDaemonState.RUNNING if running else ComxTuiDaemonState.STOPPED
    )
    start_result = ComxTuiDaemonActionResult(
        action="start",
        tmux_session=preview.tmux_session,
        tui_session_id=preview.tui_session_id,
        cwd=preview.cwd,
        command=preview.command,
        exit_code=completed_process.returncode,
        stdout=_stream_text(completed_process.stdout),
        stderr=_stream_text(completed_process.stderr),
        state=state,
        running=running,
    )
    return start_result


def stop_comx_tui_daemon(
    cwd: str | Path,
    session_id: str,
    tmux_session: str | None = None,
) -> ComxTuiDaemonActionResult:
    """Stop the detached tmux-backed comx-agent TUI daemon.

    Args:
        cwd [str | Path]: Workspace root.
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session name override.

    Returns:
        ComxTuiDaemonActionResult: Stop action result.
    """
    preview: ComxTuiDaemonCommandPreview = build_daemon_start_command(
        cwd,
        session_id,
        tmux_session=tmux_session,
    )
    command: tuple[str, ...] = ("tmux", "kill-session", "-t", preview.tmux_session)
    if not _tmux_available():
        missing_result = ComxTuiDaemonActionResult(
            action="missing",
            tmux_session=preview.tmux_session,
            tui_session_id=preview.tui_session_id,
            cwd=preview.cwd,
            command=command,
            exit_code=127,
            stdout="",
            stderr="tmux was not detected; install tmux for daemon mode.",
            state=ComxTuiDaemonState.UNAVAILABLE,
            running=False,
            warnings=("tmux was not detected; install tmux for daemon mode.",),
        )
        return missing_result

    running: bool = _tmux_has_session(preview.tmux_session)
    if not running:
        missing_daemon_result = ComxTuiDaemonActionResult(
            action="missing",
            tmux_session=preview.tmux_session,
            tui_session_id=preview.tui_session_id,
            cwd=preview.cwd,
            command=command,
            exit_code=0,
            stdout="",
            stderr="",
            state=ComxTuiDaemonState.STOPPED,
            running=False,
            warnings=("daemon session is not running.",),
        )
        return missing_daemon_result

    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    still_running: bool = completed_process.returncode != 0 and _tmux_has_session(
        preview.tmux_session
    )
    state: ComxTuiDaemonState = (
        ComxTuiDaemonState.RUNNING if still_running else ComxTuiDaemonState.STOPPED
    )
    stop_result = ComxTuiDaemonActionResult(
        action="stop",
        tmux_session=preview.tmux_session,
        tui_session_id=preview.tui_session_id,
        cwd=preview.cwd,
        command=command,
        exit_code=completed_process.returncode,
        stdout=_stream_text(completed_process.stdout),
        stderr=_stream_text(completed_process.stderr),
        state=state,
        running=still_running,
    )
    return stop_result


def attach_comx_tui_daemon(session_id: str, tmux_session: str | None = None) -> int:
    """Attach the current terminal to a running comx-agent TUI daemon.

    Args:
        session_id [str]: Durable TUI session id.
        tmux_session [str | None]: Optional tmux session name override.

    Returns:
        int: tmux attach exit code.
    """
    resolved_tmux_session: str = tmux_session or build_daemon_tmux_session_name(
        session_id
    )
    completed_process: subprocess.CompletedProcess[bytes] = subprocess.run(
        ("tmux", "attach-session", "-t", resolved_tmux_session),
        check=False,
    )
    exit_code: int = completed_process.returncode
    return exit_code
