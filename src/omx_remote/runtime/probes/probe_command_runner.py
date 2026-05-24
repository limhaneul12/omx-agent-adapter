import subprocess
from collections.abc import Callable

from omx_remote.schemas.probes.upstream_probe_schemas import ProbeProcessOutput

type ProbeRunner = Callable[[tuple[str, ...]], ProbeProcessOutput]


def run_probe_command(command: tuple[str, ...]) -> ProbeProcessOutput:
    """Run one upstream probe command.

    Args:
        command [tuple[str, ...]]: Command argv to run.

    Returns:
        ProbeProcessOutput: Captured probe output.
    """
    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            list(command),
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except FileNotFoundError as error:
        output = ProbeProcessOutput(exit_code=127, stdout="", stderr=str(error))
        return output
    except PermissionError as error:
        output = ProbeProcessOutput(exit_code=126, stdout="", stderr=str(error))
        return output
    except subprocess.TimeoutExpired as error:
        output = ProbeProcessOutput(exit_code=124, stdout="", stderr=str(error))
        return output

    output = ProbeProcessOutput(
        exit_code=completed_process.returncode,
        stdout="" if completed_process.stdout is None else completed_process.stdout,
        stderr="" if completed_process.stderr is None else completed_process.stderr,
    )
    return output
