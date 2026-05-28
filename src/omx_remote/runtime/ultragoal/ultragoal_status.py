from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.invoke.command_schemas import OmxCommandResult
from omx_remote.schemas.ultragoal.status_schemas import (
    UltragoalNativeState,
    UltragoalStatusResult,
)

ULTRAGOAL_CAPABILITY_COMMAND: tuple[str, ...] = ("ultragoal", "--help")
ULTRAGOAL_STATUS_COMMAND: tuple[str, ...] = ("ultragoal", "status", "--json")


def read_ultragoal_status(cwd: str | None = None) -> UltragoalStatusResult:
    """Read native OMX UltraGoal availability and status without mutating state.

    Args:
        cwd [str | None]: Optional working directory where native OMX probes run.

    Returns:
        UltragoalStatusResult: Typed result containing the capability and status probes.
    """
    capability_result: OmxCommandResult = run_omx_command(
        ULTRAGOAL_CAPABILITY_COMMAND,
        cwd=cwd,
    )
    if capability_result.exit_code != 0:
        unavailable_status = UltragoalStatusResult(
            state=UltragoalNativeState.UNAVAILABLE,
            supported=False,
            capability_command=ULTRAGOAL_CAPABILITY_COMMAND,
            capability_result=capability_result,
            status_command=ULTRAGOAL_STATUS_COMMAND,
            cwd=cwd,
            warnings=("omx ultragoal is not available.",),
        )
        return unavailable_status

    status_result: OmxCommandResult = run_omx_command(
        ULTRAGOAL_STATUS_COMMAND,
        cwd=cwd,
    )
    if status_result.exit_code == 0:
        available_status = UltragoalStatusResult(
            state=UltragoalNativeState.AVAILABLE,
            supported=True,
            capability_command=ULTRAGOAL_CAPABILITY_COMMAND,
            capability_result=capability_result,
            status_command=ULTRAGOAL_STATUS_COMMAND,
            status_result=status_result,
            cwd=cwd,
        )
        return available_status

    failed_status = UltragoalStatusResult(
        state=UltragoalNativeState.STATUS_FAILED,
        supported=True,
        capability_command=ULTRAGOAL_CAPABILITY_COMMAND,
        capability_result=capability_result,
        status_command=ULTRAGOAL_STATUS_COMMAND,
        status_result=status_result,
        cwd=cwd,
        warnings=("omx ultragoal status returned a non-zero exit code.",),
    )
    return failed_status
