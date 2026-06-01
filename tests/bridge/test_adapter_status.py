import asyncio
import inspect

import pytest
from pydantic import ValidationError

from omx_remote.bridge import adapter_status
from omx_remote.schemas.bridge_adapter_schemas import AdapterProbeRequest
from omx_remote.shared.exceptions import BridgeSurfaceError


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_adapter_status_is_async() -> None:
    assert inspect.iscoroutinefunction(adapter_status.read_adapter_status)


def test_read_adapter_status_accepts_typed_request() -> None:
    coroutine = adapter_status.read_adapter_status(AdapterProbeRequest(target="hermes"))

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_read_adapter_status_returns_normalized_subset(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_status,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"target":"hermes","phase":"foundation","summary":"Hermes adapter is not initialized yet; runtime evidence is still unavailable.","adapter":{"state":"not-initialized","detail":"Run init --write to create OMX-owned adapter artifacts."},"targetRuntime":{"state":"unavailable","detail":"Hermes external runtime was not detected."},"capabilities":[]}\n'
        ),
    )

    result = asyncio.run(
        adapter_status.read_adapter_status(AdapterProbeRequest(target="hermes"))
    )

    assert result.target == "hermes"
    assert result.adapter_state == "not-initialized"
    assert result.target_runtime_state == "unavailable"


def test_read_adapter_status_rejects_unparseable_json_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_status,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(BridgeSurfaceError):
        asyncio.run(
            adapter_status.read_adapter_status(AdapterProbeRequest(target="hermes"))
        )


def test_read_adapter_status_preserves_required_contract_validation(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        adapter_status,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"target":"hermes","phase":"foundation","summary":"","capabilities":[],"adapter":{"state":"not-initialized","detail":"write init"},"targetRuntime":{"state":"unavailable","detail":"missing"}}\n'
        ),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            adapter_status.read_adapter_status(AdapterProbeRequest(target="hermes"))
        )


def test_load_adapter_status_transport_payload_rejects_non_object_transport() -> None:
    with pytest.raises(BridgeSurfaceError):
        adapter_status._load_adapter_status_transport_payload("[]")


def test_load_adapter_status_transport_payload_rejects_non_string_adapter_state() -> (
    None
):
    with pytest.raises(BridgeSurfaceError):
        adapter_status._load_adapter_status_transport_payload(
            '{"target":"hermes","phase":"foundation","summary":"ok","capabilities":[],"adapter":{"state":42,"detail":"write init","configPath":"/tmp/adapter.json","envelopePath":"/tmp/envelope.json"},"targetRuntime":{"state":"unavailable","detail":"missing"}}'
        )


def test_load_adapter_status_transport_payload_rejects_non_string_config_path() -> None:
    with pytest.raises(BridgeSurfaceError):
        adapter_status._load_adapter_status_transport_payload(
            '{"target":"hermes","phase":"foundation","summary":"ok","capabilities":[],"adapter":{"state":"not-initialized","detail":"write init","configPath":42,"envelopePath":"/tmp/envelope.json"},"targetRuntime":{"state":"unavailable","detail":"missing"}}'
        )


def test_load_adapter_status_transport_payload_preserves_live_required_bridge_fields() -> (
    None
):
    result = adapter_status._load_adapter_status_transport_payload(
        '{"target":"hermes","phase":"foundation","summary":"ok","capabilities":[],"adapter":{"state":"not-initialized","detail":"write init","configPath":"/tmp/adapter.json","envelopePath":"/tmp/envelope.json"},"targetRuntime":{"state":"unavailable","detail":"missing","evidence":{}},"schemaVersion":"1.0","timestamp":"2026-05-04T08:02:34.415Z"}'
    )

    assert result == {
        "target": "hermes",
        "phase": "foundation",
        "summary": "ok",
        "capabilities": [],
        "adapter": {
            "state": "not-initialized",
            "detail": "write init",
            "configPath": "/tmp/adapter.json",
            "envelopePath": "/tmp/envelope.json",
        },
        "targetRuntime": {
            "state": "unavailable",
            "detail": "missing",
            "evidence": {},
        },
    }
