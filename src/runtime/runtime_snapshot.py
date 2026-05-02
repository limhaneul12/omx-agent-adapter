import asyncio

from execution.invoke import run_omx_command
from schemas.runtime_schemas import RuntimeModeStatus, RuntimeStatus

IDLE_RUNTIME_SUMMARY = "No active modes."
ACTIVE_MODE_MARKER = "active"
KNOWN_MODE_STATUS_MARKERS: tuple[RuntimeModeStatus, ...] = (
    "active",
    "paused",
    "idle",
    "unknown",
)


async def read_runtime_status() -> RuntimeStatus:
    """Reads and normalizes OMX runtime status.

    Args:
        None: This function does not accept caller-provided arguments.

    Returns:
        RuntimeStatus: Normalized runtime status built from `omx status` stdout or stderr fallback output.
    """
    command_result = await asyncio.to_thread(run_omx_command, ["status"])
    stdout: str = command_result.stdout.strip()
    summary: str = stdout or command_result.stderr.strip()
    has_active_modes: bool | None = _infer_has_active_modes(stdout, summary)
    active_mode_names: list[str] = _extract_active_mode_names(stdout)
    mode_statuses: dict[str, RuntimeModeStatus] = _extract_mode_statuses(stdout)
    result: RuntimeStatus = RuntimeStatus.model_validate(
        {
            "summary": summary,
            "has_active_modes": has_active_modes,
            "active_mode_names": active_mode_names,
            "mode_statuses": mode_statuses,
        }
    )
    return result


def _infer_has_active_modes(stdout: str, summary: str) -> bool | None:
    has_active_modes: bool | None
    if stdout:
        has_active_modes = summary != IDLE_RUNTIME_SUMMARY
        return has_active_modes
    has_active_modes = None
    return has_active_modes


def _extract_active_mode_names(stdout: str) -> list[str]:
    mode_statuses: dict[str, RuntimeModeStatus] = _extract_mode_statuses(stdout)
    active_mode_names: list[str] = [
        mode_name
        for mode_name, status_text in mode_statuses.items()
        if status_text == ACTIVE_MODE_MARKER
    ]
    return active_mode_names


def _extract_mode_statuses(stdout: str) -> dict[str, RuntimeModeStatus]:
    if not stdout or stdout == IDLE_RUNTIME_SUMMARY:
        empty_mode_statuses: dict[str, RuntimeModeStatus] = {}
        return empty_mode_statuses

    mode_statuses: dict[str, RuntimeModeStatus] = {}
    for line in stdout.splitlines():
        parsed_mode_status: tuple[str, RuntimeModeStatus] | None = _parse_mode_status(line)
        if parsed_mode_status is None:
            continue
        mode_name: str
        status_text: RuntimeModeStatus
        mode_name, status_text = parsed_mode_status
        mode_statuses[mode_name] = status_text
    return mode_statuses


def _parse_active_mode_name(line: str) -> str | None:
    parsed_mode_status: tuple[str, RuntimeModeStatus] | None = _parse_mode_status(line)
    if parsed_mode_status is None:
        return None

    mode_name: str
    status_text: RuntimeModeStatus
    mode_name, status_text = parsed_mode_status
    if status_text != ACTIVE_MODE_MARKER:
        return None

    active_mode_name: str = mode_name
    return active_mode_name


def _parse_mode_status(line: str) -> tuple[str, RuntimeModeStatus] | None:
    if ":" not in line:
        return None

    mode_name: str
    status_text: str
    mode_name, status_text = line.split(":", maxsplit=1)
    normalized_mode_name: str = mode_name.strip()
    normalized_status_text: str = status_text.strip().lower()

    if not normalized_mode_name:
        return None

    parsed_mode_status: tuple[str, RuntimeModeStatus] | None
    if normalized_status_text == "active":
        parsed_mode_status = (normalized_mode_name, "active")
        return parsed_mode_status
    if normalized_status_text == "paused":
        parsed_mode_status = (normalized_mode_name, "paused")
        return parsed_mode_status
    if normalized_status_text == "idle":
        parsed_mode_status = (normalized_mode_name, "idle")
        return parsed_mode_status
    if normalized_status_text:
        parsed_mode_status = (normalized_mode_name, "unknown")
        return parsed_mode_status

    parsed_mode_status = None
    return parsed_mode_status
