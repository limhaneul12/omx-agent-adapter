import subprocess
from collections.abc import Sequence

from schemas.invoke_schemas import OmxCommandResult


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
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        command_arguments,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    command_result: OmxCommandResult = OmxCommandResult(
        exit_code=completed_process.returncode,
        stdout=completed_process.stdout,
        stderr=completed_process.stderr,
    )
    return command_result
