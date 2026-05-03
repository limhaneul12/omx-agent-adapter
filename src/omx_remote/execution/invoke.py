import subprocess
from collections.abc import Sequence

from omx_remote.schemas.invoke_schemas import OmxCommandResult


def _command_failure_exit_code(error: OSError) -> int:
    if isinstance(error, FileNotFoundError):
        return 127
    if isinstance(error, PermissionError):
        return 126
    return 1


def _normalize_completed_process_stream_text(stream_text: str | None) -> str:
    if stream_text is None:
        normalized_stream_text: str = ""
        return normalized_stream_text

    normalized_stream_text = stream_text
    return normalized_stream_text


def run_omx_command(
    arguments: Sequence[str],
    cwd: str | None = None,
) -> OmxCommandResult:
    """Runs an OMX subprocess command.

    Args:
        arguments [Sequence[str]]: OMX command arguments without the leading executable name.
        cwd [str | None]: Working directory used when the OMX command runs.

    Returns:
        OmxCommandResult: Completed OMX command result with shared exit-code, stdout, and stderr fields.
    """
    command_arguments: list[str] = ["omx", *arguments]
    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            command_arguments,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return OmxCommandResult(
            exit_code=_command_failure_exit_code(error),
            stdout="",
            stderr=str(error),
        )
    stdout_text: str = _normalize_completed_process_stream_text(
        completed_process.stdout
    )
    stderr_text: str = _normalize_completed_process_stream_text(
        completed_process.stderr
    )
    command_result: OmxCommandResult = OmxCommandResult(
        exit_code=completed_process.returncode,
        stdout=stdout_text,
        stderr=stderr_text,
    )
    return command_result
