import asyncio

from execution.invoke import run_omx_command
from schemas.bridge_schemas import AdapterProbeRequest, AdapterProbeSnapshot
from shared.exceptions.bridge_exceptions import BridgeSurfaceError
from shared.json_transport import load_json_object_stdout


async def probe_adapter(request: AdapterProbeRequest) -> AdapterProbeSnapshot:
    """Reads one typed adapter probe surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> probe --json`.

    Returns:
        AdapterProbeSnapshot: Normalized probe contract built from the live adapt probe payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        ["adapt", request.target, "probe", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterProbeSnapshot = _normalize_adapter_probe(stdout)
    return result


def _normalize_adapter_probe(stdout: str) -> AdapterProbeSnapshot:
    """Normalizes one `omx adapt <target> probe --json` payload.

    Args:
        stdout [str]: Raw stdout text returned from the adapt probe command.

    Returns:
        AdapterProbeSnapshot: Validated normalized probe contract.

    Raises:
        BridgeSurfaceError: Raised when the transport is empty, not JSON, or not a JSON object.
    """
    parsed_payload: dict[str, object] = load_json_object_stdout(
        stdout,
        command_name="omx adapt probe",
        error_type=BridgeSurfaceError,
    )

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
        "capabilities": parsed_payload.get("capabilities", []),
        "target_runtime_state": target_runtime_state,
        "target_runtime_detail": target_runtime_detail,
    }
    result: AdapterProbeSnapshot = AdapterProbeSnapshot.model_validate(
        normalized_payload
    )
    return result
