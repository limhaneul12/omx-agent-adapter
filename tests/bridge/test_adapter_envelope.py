import asyncio
import inspect

import pytest
from pydantic import ValidationError

from bridge import adapter_envelope
from schemas.bridge_schemas import AdapterProbeRequest
from shared.exceptions.bridge_exceptions import BridgeSurfaceError


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_adapter_envelope_is_async() -> None:
    assert inspect.iscoroutinefunction(adapter_envelope.read_adapter_envelope)


def test_read_adapter_envelope_accepts_typed_request() -> None:
    coroutine = adapter_envelope.read_adapter_envelope(AdapterProbeRequest(target="hermes"))

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_adapter_envelope_returns_normalized_subset(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_envelope,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"target":"hermes","displayName":"Hermes","summary":"Foundation seam for an OMX-owned adapter around Hermes ACP, gateway, and persistent-session surfaces.","capabilities":[],"targetRuntime":{"state":"unavailable","detail":"Hermes external runtime was not detected."}}\n'
        ),
    )

    result = asyncio.run(
        adapter_envelope.read_adapter_envelope(AdapterProbeRequest(target="hermes"))
    )

    assert result.target == "hermes"
    assert result.display_name == "Hermes"
    assert result.target_runtime_state == "unavailable"


def test_read_adapter_envelope_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_envelope,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(BridgeSurfaceError):
        asyncio.run(
            adapter_envelope.read_adapter_envelope(AdapterProbeRequest(target="hermes"))
        )


def test_read_adapter_envelope_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_envelope,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"target":"hermes"}\n'),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            adapter_envelope.read_adapter_envelope(AdapterProbeRequest(target="hermes"))
        )


def test_load_adapter_envelope_transport_payload_rejects_non_object_transport() -> None:
    with pytest.raises(BridgeSurfaceError):
        adapter_envelope._load_adapter_envelope_transport_payload("[]")
