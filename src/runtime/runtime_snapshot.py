"""Normalizes OMX runtime status output into stable adapter contracts."""

import asyncio

from execution.invoke import run_omx_command
from schemas.runtime_schemas import (
    RuntimeModeSnapshot,
    RuntimeModeStatus,
    RuntimeStatus,
    RuntimeStatusAnomaly,
)

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
    stderr: str = command_result.stderr.strip()
    summary: str = stdout or stderr
    has_active_modes: bool | None = _infer_has_active_modes(stdout, summary)
    active_mode_names: list[str] = _extract_active_mode_names(stdout)
    mode_statuses: dict[str, RuntimeModeStatus] = _extract_mode_statuses(stdout)
    mode_snapshots: list[RuntimeModeSnapshot] = _build_mode_snapshots(mode_statuses)
    anomalies: list[RuntimeStatusAnomaly] = _build_runtime_status_anomalies(
        stdout=stdout,
        stderr=stderr,
    )
    result: RuntimeStatus = RuntimeStatus.model_validate(
        {
            "summary": summary,
            "has_active_modes": has_active_modes,
            "active_mode_names": active_mode_names,
            "mode_snapshots": mode_snapshots,
            "mode_statuses": mode_statuses,
            "anomalies": anomalies,
        }
    )
    return result


def _infer_has_active_modes(stdout: str, summary: str) -> bool | None:
    """Infers whether OMX currently reports active modes.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.
        summary [str]: Summary text selected for the runtime status surface.

    Returns:
        bool | None: Boolean activity signal when stdout is available, otherwise `None` when the state cannot be inferred.
    """
    has_active_modes: bool | None
    if stdout:
        has_active_modes = summary != IDLE_RUNTIME_SUMMARY
        return has_active_modes
    has_active_modes = None
    return has_active_modes


def _extract_active_mode_names(stdout: str) -> list[str]:
    """Extracts active runtime mode names from status output.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.

    Returns:
        list[str]: Mode names whose parsed status token resolves to `active`.
    """
    mode_statuses: dict[str, RuntimeModeStatus] = _extract_mode_statuses(stdout)
    active_mode_names: list[str] = [
        mode_name
        for mode_name, status_text in mode_statuses.items()
        if status_text == ACTIVE_MODE_MARKER
    ]
    return active_mode_names


def _extract_mode_statuses(stdout: str) -> dict[str, RuntimeModeStatus]:
    """Extracts typed runtime mode statuses from status output.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.

    Returns:
        dict[str, RuntimeModeStatus]: Mapping from mode name to normalized runtime status token.
    """
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


def _build_mode_snapshots(
    mode_statuses: dict[str, RuntimeModeStatus],
) -> list[RuntimeModeSnapshot]:
    """Builds per-mode runtime snapshot objects from normalized statuses.

    Args:
        mode_statuses [dict[str, RuntimeModeStatus]]: Normalized mode-status mapping keyed by mode name.

    Returns:
        list[RuntimeModeSnapshot]: Ordered runtime mode snapshots derived from the normalized status mapping.
    """
    mode_snapshots: list[RuntimeModeSnapshot] = [
        RuntimeModeSnapshot(name=mode_name, status=status_text)
        for mode_name, status_text in mode_statuses.items()
    ]
    return mode_snapshots


def _build_runtime_status_anomalies(
    *,
    stdout: str,
    stderr: str,
) -> list[RuntimeStatusAnomaly]:
    """Builds normalized runtime anomalies from status transport output.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.
        stderr [str]: Normalized stderr text returned from `omx status`.

    Returns:
        list[RuntimeStatusAnomaly]: Runtime anomalies derived from empty transport output, stderr fallback usage, unparseable stdout, and unknown mode-status tokens.
    """
    anomalies: list[RuntimeStatusAnomaly] = []

    if not stdout and not stderr:
        anomalies.append(
            RuntimeStatusAnomaly(
                category="empty_transport_output",
                message="omx status returned no stdout or stderr output",
            )
        )
        return anomalies

    if not stdout and stderr:
        anomalies.append(
            RuntimeStatusAnomaly(
                category="stderr_fallback",
                message=stderr,
            )
        )
        return anomalies

    if not stdout:
        return anomalies

    mode_statuses: dict[str, RuntimeModeStatus] = _extract_mode_statuses(stdout)
    if not mode_statuses and stdout != IDLE_RUNTIME_SUMMARY:
        anomalies.append(
            RuntimeStatusAnomaly(
                category="unparseable_stdout",
                message=stdout,
            )
        )

    line: str
    for line in stdout.splitlines():
        parsed_mode_status: tuple[str, RuntimeModeStatus] | None = _parse_mode_status(line)
        if parsed_mode_status is None:
            continue

        mode_name: str
        status_text: RuntimeModeStatus
        mode_name, status_text = parsed_mode_status
        if status_text != "unknown":
            continue

        raw_status_text: str = line.split(":", maxsplit=1)[1].strip()
        anomalies.append(
            RuntimeStatusAnomaly(
                category="unknown_mode_status",
                message=raw_status_text,
                mode_name=mode_name,
            )
        )

    return anomalies


def _parse_active_mode_name(line: str) -> str | None:
    """Parses an active mode name from one status line.

    Args:
        line [str]: One line from normalized `omx status` stdout.

    Returns:
        str | None: Active mode name when the line describes an active mode, otherwise `None`.
    """
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
    """Parses one runtime mode status line into a typed pair.

    Args:
        line [str]: One line from normalized `omx status` stdout.

    Returns:
        tuple[str, RuntimeModeStatus] | None: Parsed mode name and normalized status token when the line matches the expected shape.
    """
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
