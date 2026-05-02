import subprocess
from collections.abc import Sequence


def run_omx_command(
    arguments: Sequence[str],
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Runs an OMX subprocess command.

    Args:
        arguments [Sequence[str]]: OMX command arguments without the leading executable name.
        cwd [str | None]: Working directory used when the OMX command runs.

    Returns:
        subprocess.CompletedProcess[str]: Completed OMX process result with captured stdout and stderr text streams.
    """
    command_arguments: list[str] = ["omx", *arguments]
    command_result: subprocess.CompletedProcess[str] = subprocess.run(
        command_arguments,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return command_result
