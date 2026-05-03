import asyncio

from execution.invoke import run_omx_command
from schemas.bridge_schemas import AdapterEnvelopeSnapshot, AdapterProbeRequest
from shared.exceptions.bridge_exceptions import BridgeSurfaceError
from shared.json_transport import load_json_object_stdout


async def read_adapter_envelope(request: AdapterProbeRequest) -> AdapterEnvelopeSnapshot:
    """Reads one typed adapter envelope surface.

    Args:
        request [AdapterProbeRequest]: Typed request boundary for `omx adapt <target> envelope --json`.

    Returns:
        AdapterEnvelopeSnapshot: Normalized envelope contract built from the live adapt envelope payload.
    """
    command_result = await asyncio.to_thread(
        run_omx_command,
        ["adapt", request.target, "envelope", "--json"],
    )
    stdout: str = command_result.stdout.strip()
    result: AdapterEnvelopeSnapshot = _normalize_adapter_envelope(stdout)
    return result


def _normalize_adapter_envelope(stdout: str) -> AdapterEnvelopeSnapshot:
    """Normalizes one `omx adapt <target> envelope --json` payload."""
    parsed_payload: dict[str, object] = load_json_object_stdout(
        stdout,
        command_name="omx adapt envelope",
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
        "display_name": parsed_payload.get("displayName"),
        "summary": parsed_payload.get("summary"),
        "capabilities": parsed_payload.get("capabilities", []),
        "target_runtime_state": target_runtime_state,
        "target_runtime_detail": target_runtime_detail,
    }
    result: AdapterEnvelopeSnapshot = AdapterEnvelopeSnapshot.model_validate(
        normalized_payload
    )
    return result
