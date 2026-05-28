import orjson

from omx_remote.adapter_types.runtime_types import ActiveRuntimeModesTransportPayload
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.execution.invoke import run_omx_command
from omx_remote.schemas.runtime.status_schemas import ActiveRuntimeModes
from omx_remote.shared.exceptions import RuntimeSurfaceError


async def read_active_runtime_modes() -> ActiveRuntimeModes:
    """Reads and normalizes OMX active runtime modes.

    Returns:
        ActiveRuntimeModes: Typed active-mode contract built from `omx state list-active --json`.
    """
    command_result = await run_blocking_call(
        run_omx_command,
        ["state", "list-active", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: ActiveRuntimeModes = _normalize_active_runtime_modes(stdout)
    return result


def _load_active_runtime_modes_payload(stdout: str) -> ActiveRuntimeModesTransportPayload:
    """Loads one active-runtime-modes transport payload from raw stdout.
    
    Args:
        stdout [str]: Function argument.
    
    Returns:
        ActiveRuntimeModesTransportPayload: Function return value.
    """
    if not stdout:
        raise RuntimeSurfaceError("omx state list-active returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise RuntimeSurfaceError(
            "omx state list-active returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise RuntimeSurfaceError(
            "omx state list-active returned a non-object JSON payload"
        )

    active_modes_payload: object | None = parsed_payload.get("active_modes")
    if not isinstance(active_modes_payload, list):
        raise RuntimeSurfaceError(
            "omx state list-active returned a non-list active_modes payload"
        )

    normalized_active_modes: list[str] = []
    active_mode: object
    for active_mode in active_modes_payload:
        if not isinstance(active_mode, str):
            raise RuntimeSurfaceError(
                "omx state list-active returned a non-string active mode entry"
            )
        normalized_active_modes.append(active_mode)

    result = ActiveRuntimeModesTransportPayload(
        active_modes=normalized_active_modes,
    )
    return result

def _normalize_active_runtime_modes(stdout: str) -> ActiveRuntimeModes:
    """Normalizes `omx state list-active --json` stdout into a stable contract.

    Args:
        stdout [str]: Raw stdout text returned from `omx state list-active --json`.

    Returns:
        ActiveRuntimeModes: Validated active runtime mode contract.

    Raises:
        RuntimeSurfaceError: Raised when the transport is empty, not JSON, or not a JSON object.
    """
    parsed_payload: ActiveRuntimeModesTransportPayload = _load_active_runtime_modes_payload(
        stdout
    )

    result: ActiveRuntimeModes = ActiveRuntimeModes.model_validate(parsed_payload)
    return result
