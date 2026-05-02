import asyncio
import inspect

import pytest
from pydantic import ValidationError

from bridge import adapter_status
from schemas.bridge_schemas import AdapterProbeRequest
from shared.exceptions.bridge_exceptions import BridgeSurfaceError


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


def test_read_adapter_status_preserves_required_contract_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_status,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"target":"hermes"}\n'),
    )

    with pytest.raises(ValidationError):
        asyncio.run(
            adapter_status.read_adapter_status(AdapterProbeRequest(target="hermes"))
        )
