"""Normalizes OMX runtime status output into stable adapter contracts."""

from __future__ import annotations

from omx_remote.adapter_types.type_contract import runtime_status_contract_type
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.runtime.status_schemas import (
    RuntimeModeSnapshot,
    RuntimeModeStatus,
    RuntimeStatus,
    RuntimeStatusAnomaly,
    RuntimeStatusRequest,
)


async def read_runtime_status(
    request: RuntimeStatusRequest | None = None,
) -> RuntimeStatus:
    """Reads and normalizes OMX runtime status.

    Args:
        request [RuntimeStatusRequest | None]: Typed runtime status request. The current surface does not expose request options yet.

    Returns:
        RuntimeStatus: Normalized runtime status built from `omx status` stdout or stderr fallback output.
    """
    normalized_request: RuntimeStatusRequest
    if request is None:
        normalized_request = RuntimeStatusRequest()
    else:
        normalized_request = request
    command_result = await run_blocking_call(run_omx_command, ["status"])
    stdout: str = command_result.stdout.strip()
    stderr: str = command_result.stderr.strip()
    summary: str
    if stdout:
        summary = stdout
    else:
        summary = stderr
    mode_statuses: dict[str, RuntimeModeStatus] = _extract_mode_statuses(stdout)
    has_active_modes: bool | None = _infer_has_active_modes(
        stdout=stdout,
        summary=summary,
        mode_statuses=mode_statuses,
    )
    active_mode_names: list[str] = _extract_active_mode_names(stdout)
    mode_snapshots: list[RuntimeModeSnapshot] = _build_mode_snapshots(stdout)
    anomalies: list[RuntimeStatusAnomaly] = _build_runtime_status_anomalies(
        stdout=stdout,
        stderr=stderr,
    )
    has_anomalies: bool = bool(anomalies)
    anomaly_count: int = len(anomalies)
    result: RuntimeStatus = RuntimeStatus.model_validate(
        {
            "summary": summary,
            "has_active_modes": has_active_modes,
            "active_mode_names": active_mode_names,
            "mode_snapshots": mode_snapshots,
            "mode_statuses": mode_statuses,
            "anomalies": anomalies,
            "has_anomalies": has_anomalies,
            "anomaly_count": anomaly_count,
        }
    )
    _ = normalized_request
    return result


def _infer_has_active_modes(
    stdout: str,
    summary: str,
    mode_statuses: dict[str, RuntimeModeStatus],
) -> bool | None:
    """Infers whether OMX currently reports active modes.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.
        summary [str]: Summary text selected for the runtime status surface.
        mode_statuses [dict[str, RuntimeModeStatus]]: Parsed per-mode status tokens from stdout.

    Returns:
        bool | None: Boolean activity signal when stdout is available, otherwise `None` when the state cannot be inferred.
    """
    has_active_modes: bool | None
    if stdout and mode_statuses:
        if any(mode_status is runtime_status_contract_type.ACTIVE_MODE_MARKER for mode_status in mode_statuses.values()):
            has_active_modes = True
            return has_active_modes
        if any(
            mode_status is RuntimeModeStatus.UNKNOWN
            for mode_status in mode_statuses.values()
        ):
            has_active_modes = None
            return has_active_modes
        has_active_modes = False
        return has_active_modes
    if stdout:
        has_active_modes = summary != runtime_status_contract_type.IDLE_RUNTIME_SUMMARY
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
        if status_text is runtime_status_contract_type.ACTIVE_MODE_MARKER
    ]
    return active_mode_names


def _extract_mode_status_entries(
    stdout: str,
) -> list[tuple[str, RuntimeModeStatus, str]]:
    """Extracts typed runtime mode-status entries from status output.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.

    Returns:
        list[tuple[str, RuntimeModeStatus, str]]: Ordered runtime mode entries containing mode name, normalized status token, and raw status text.
    """
    if not stdout or stdout == runtime_status_contract_type.IDLE_RUNTIME_SUMMARY:
        empty_mode_status_entries: list[tuple[str, RuntimeModeStatus, str]] = []
        return empty_mode_status_entries

    mode_status_entries: list[tuple[str, RuntimeModeStatus, str]] = []
    for line in stdout.splitlines():
        parsed_mode_status_entry: tuple[str, RuntimeModeStatus, str] | None = (
            _parse_mode_status_entry(line)
        )
        if parsed_mode_status_entry is None:
            continue
        mode_status_entries.append(parsed_mode_status_entry)
    return mode_status_entries


def _extract_mode_statuses(stdout: str) -> dict[str, RuntimeModeStatus]:
    """Extracts typed runtime mode statuses from status output.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.

    Returns:
        dict[str, RuntimeModeStatus]: Mapping from mode name to normalized runtime status token.
    """
    mode_status_entries: list[tuple[str, RuntimeModeStatus, str]] = _extract_mode_status_entries(
        stdout
    )
    mode_statuses: dict[str, RuntimeModeStatus] = {
        mode_name: status_text
        for mode_name, status_text, raw_status_text in mode_status_entries
    }
    return mode_statuses


def _build_mode_snapshots(
    stdout: str,
) -> list[RuntimeModeSnapshot]:
    """Builds per-mode runtime snapshot objects from normalized statuses.

    Args:
        stdout [str]: Normalized stdout text returned from `omx status`.

    Returns:
        list[RuntimeModeSnapshot]: Ordered runtime mode snapshots derived from parsed mode-status entries.
    """
    mode_status_entries: list[tuple[str, RuntimeModeStatus, str]] = _extract_mode_status_entries(
        stdout
    )
    mode_snapshots: list[RuntimeModeSnapshot] = [
        RuntimeModeSnapshot(
            name=mode_name,
            status=status_text,
            raw_status_text=raw_status_text,
            has_uncertainty=status_text == RuntimeModeStatus.UNKNOWN,
        )
        for mode_name, status_text, raw_status_text in mode_status_entries
    ]
    return mode_snapshots


def _build_runtime_status_anomalies(
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
    if not mode_statuses and stdout != runtime_status_contract_type.IDLE_RUNTIME_SUMMARY:
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
        if status_text != RuntimeModeStatus.UNKNOWN:
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


def _parse_mode_status_entry(line: str) -> tuple[str, RuntimeModeStatus, str] | None:
    """Parses one runtime mode status line into a typed entry.

    Args:
        line [str]: One line from normalized `omx status` stdout.

    Returns:
        tuple[str, RuntimeModeStatus, str] | None: Parsed mode name, normalized status token, and raw status text when the line matches the expected shape.
    """
    if ":" not in line:
        missing_entry: tuple[str, RuntimeModeStatus, str] | None = None
        return missing_entry

    mode_name: str
    status_text: str
    mode_name, status_text = line.split(":", maxsplit=1)
    normalized_mode_name: str = mode_name.strip()
    normalized_status_text: str = status_text.strip().lower()
    raw_status_text: str = status_text.strip()

    if not normalized_mode_name:
        missing_entry = None
        return missing_entry

    status_prefix: str
    normalized_status: RuntimeModeStatus
    for status_prefix, normalized_status in runtime_status_contract_type.RUNTIME_STATUS_PREFIXES:
        if normalized_status_text == status_prefix:
            parsed_mode_status_entry = (
                normalized_mode_name,
                normalized_status,
                raw_status_text,
            )
            return parsed_mode_status_entry
        if normalized_status_text.startswith(f"{status_prefix} "):
            parsed_mode_status_entry = (
                normalized_mode_name,
                normalized_status,
                raw_status_text,
            )
            return parsed_mode_status_entry

    parsed_mode_status_entry = (
        normalized_mode_name,
        RuntimeModeStatus.UNKNOWN,
        raw_status_text,
    )
    return parsed_mode_status_entry


def _parse_mode_status(line: str) -> tuple[str, RuntimeModeStatus] | None:
    """Parses one runtime mode status line into a typed pair.
    
    Args:
        line [str]: Function argument.
    
    Returns:
        tuple[str, RuntimeModeStatus] | None: Function return value.
    """
    parsed_mode_status_entry: tuple[str, RuntimeModeStatus, str] | None = (
        _parse_mode_status_entry(line)
    )
    if parsed_mode_status_entry is None:
        missing_mode_status: tuple[str, RuntimeModeStatus] | None = None
        return missing_mode_status

    mode_name: str
    status_text: RuntimeModeStatus
    raw_status_text: str
    mode_name, status_text, raw_status_text = parsed_mode_status_entry
    _ = raw_status_text
    result: tuple[str, RuntimeModeStatus] = (mode_name, status_text)
    return result


def _parse_active_mode_name(line: str) -> str | None:
    """Parses one active runtime mode name from a status line.
    
    Args:
        line [str]: Function argument.
    
    Returns:
        str | None: Function return value.
    """
    parsed_mode_status_entry: tuple[str, RuntimeModeStatus, str] | None = (
        _parse_mode_status_entry(line)
    )
    if parsed_mode_status_entry is None:
        missing_mode_name: str | None = None
        return missing_mode_name

    mode_name: str
    status_text: RuntimeModeStatus
    raw_status_text: str
    mode_name, status_text, raw_status_text = parsed_mode_status_entry
    _ = raw_status_text
    if status_text != RuntimeModeStatus.ACTIVE:
        inactive_mode_name: str | None = None
        return inactive_mode_name
    return mode_name
