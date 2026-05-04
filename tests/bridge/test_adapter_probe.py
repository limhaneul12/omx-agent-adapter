import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.bridge import adapter_probe
from omx_remote.schemas.bridge_schemas import AdapterProbeRequest
from omx_remote.shared.exceptions import BridgeSurfaceError


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_probe_adapter_is_async() -> None:
    assert inspect.iscoroutinefunction(adapter_probe.probe_adapter)


def test_probe_adapter_accepts_typed_request() -> None:
    coroutine = adapter_probe.probe_adapter(AdapterProbeRequest(target="hermes"))

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_probe_adapter_returns_normalized_subset(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_probe,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"target":"hermes","phase":"foundation","summary":"Hermes probe inspected ACP, gateway, and session-store evidence from the external runtime.","capabilities":[{"id":"foundation-reporting","label":"Foundation reporting surface","ownership":"shared-contract","status":"ready","summary":"Probe, status, envelope, init, and doctor share a target-agnostic output contract."}],"targetRuntime":{"state":"unavailable","detail":"Hermes external runtime was not detected."}}\n'
        ),
    )

    result = asyncio.run(adapter_probe.probe_adapter(AdapterProbeRequest(target="hermes")))

    assert result.target == "hermes"
    assert result.phase == "foundation"
    assert result.target_runtime_state == "unavailable"
    assert result.capabilities[0].id == "foundation-reporting"


def test_probe_adapter_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_probe,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(BridgeSurfaceError):
        asyncio.run(adapter_probe.probe_adapter(AdapterProbeRequest(target="hermes")))


def test_probe_adapter_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_probe,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"target":"hermes"}\n'),
    )

    with pytest.raises(ValidationError):
        asyncio.run(adapter_probe.probe_adapter(AdapterProbeRequest(target="hermes")))


def test_load_adapter_probe_transport_payload_rejects_non_object_transport() -> None:
    with pytest.raises(BridgeSurfaceError):
        adapter_probe._load_adapter_probe_transport_payload("[]")


def test_load_adapter_probe_transport_payload_preserves_live_required_bridge_fields() -> None:
    result = adapter_probe._load_adapter_probe_transport_payload(
        '{"target":"hermes","phase":"foundation","summary":"ok","capabilities":[],"targetRuntime":{"state":"unavailable","detail":"missing","evidence":{}},"schemaVersion":"1.0","timestamp":"2026-05-04T08:02:34.260Z"}'
    )

    assert result == {
        "target": "hermes",
        "phase": "foundation",
        "summary": "ok",
        "capabilities": [],
        "targetRuntime": {
            "state": "unavailable",
            "detail": "missing",
            "evidence": {},
        },
    }
