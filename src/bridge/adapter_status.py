import asyncio

from execution.invoke import run_omx_command
from schemas.bridge_schemas import AdapterProbeRequest, AdapterStatusSnapshot
from shared.exceptions.bridge_exceptions import BridgeSurfaceError
from shared.json_transport import load_json_object_stdout


async def read_adapter_status(request: AdapterProbeRequest) -> AdapterStatusSnapshot:
    """Reads one typed adapter status surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> status --json`.

    Returns:
        AdapterStatusSnapshot: Normalized status contract built from the live adapt status payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        ["adapt", request.target, "status", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterStatusSnapshot = _normalize_adapter_status(stdout)
    return result


def _normalize_adapter_status(stdout: str) -> AdapterStatusSnapshot:
    """Normalizes one `omx adapt <target> status --json` payload."""
    parsed_payload: dict[str, object] = load_json_object_stdout(
        stdout,
        command_name="omx adapt status",
        error_type=BridgeSurfaceError,
    )

    adapter_payload: object | None = parsed_payload.get("adapter")
    adapter_state: object | None = None
    adapter_detail: object | None = None
    if isinstance(adapter_payload, dict):
        adapter_state = adapter_payload.get("state")
        adapter_detail = adapter_payload.get("detail")

    target_runtime_payload: object | None = parsed_payload.get("targetRuntime")
    target_runtime_state: object | None = None
    target_runtime_detail: object | None = None
    if isinstance(target_runtime_payload, dict):
        target_runtime_state = target_runtime_payload.get("state")
        target_runtime_detail = target_runtime_payload.get("detail")

    normalized_payload: dict[str, object] = {
        "target": parsed_payload.get("target"),
        "phase": parsed_payload.get("phase"),
        "summary": parsed_payload.get("summary"),
        "adapter_state": adapter_state,
        "adapter_detail": adapter_detail,
        "target_runtime_state": target_runtime_state,
        "target_runtime_detail": target_runtime_detail,
        "capabilities": parsed_payload.get("capabilities", []),
    }
    result: AdapterStatusSnapshot = AdapterStatusSnapshot.model_validate(
        normalized_payload
    )
    return result
