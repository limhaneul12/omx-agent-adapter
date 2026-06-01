from shutil import which

from omx_remote.schemas.preflight_schemas import (
    PreflightCategory,
    PreflightCheckResult,
    PreflightSeverity,
)


def check_tool_available(tool_name: str) -> PreflightCheckResult:
    """Check whether an executable is available on PATH.

    Args:
        tool_name [str]: Executable name to find.

    Returns:
        PreflightCheckResult: Tool availability preflight result.
    """
    tool_path: str | None = which(tool_name)
    if tool_path is None:
        missing_result = PreflightCheckResult(
            category=PreflightCategory.TOOL_AVAILABILITY,
            severity=PreflightSeverity.BLOCKER,
            summary=f"{tool_name} is not available",
            detail=f"{tool_name} was not found on PATH.",
            blocks_execution=True,
        )
        return missing_result

    available_result = PreflightCheckResult(
        category=PreflightCategory.TOOL_AVAILABILITY,
        severity=PreflightSeverity.INFO,
        summary=f"{tool_name} is available",
        detail=f"{tool_name} resolves to {tool_path}.",
        blocks_execution=False,
        evidence=tool_path,
    )
    return available_result
