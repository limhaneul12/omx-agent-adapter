import asyncio

import pytest
from pydantic import ValidationError

from omx_remote.runtime import active_runtime_modes
from omx_remote.shared.exceptions import RuntimeSurfaceError


class DummyResult:
    def __init__(self, stdout: str = "ok", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_active_runtime_modes_returns_typed_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        active_runtime_modes,
        "run_omx_command",
        lambda args: DummyResult(stdout='{"active_modes":["ralph","run"]}\n'),
    )

    result = asyncio.run(active_runtime_modes.read_active_runtime_modes())

    assert result.active_modes == ("ralph", "run")


def test_read_active_runtime_modes_rejects_unparseable_json_transport(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        active_runtime_modes,
        "run_omx_command",
        lambda args: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(active_runtime_modes.read_active_runtime_modes())


def test_read_active_runtime_modes_rejects_non_mapping_transport(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        active_runtime_modes,
        "run_omx_command",
        lambda args: DummyResult(stdout='["ralph","run"]\n'),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(active_runtime_modes.read_active_runtime_modes())


def test_read_active_runtime_modes_preserves_contract_validation_boundary(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        active_runtime_modes,
        "run_omx_command",
        lambda args: DummyResult(stdout='{"active_modes":["ralph"],"unexpected":true}\n'),
    )

    result = asyncio.run(active_runtime_modes.read_active_runtime_modes())

    assert result.active_modes == ("ralph",)


def test_read_active_runtime_modes_invokes_expected_state_command(monkeypatch) -> None:
    seen_arguments: list[list[str]] = []

    def fake_run(arguments: list[str]) -> DummyResult:
        seen_arguments.append(arguments)
        return DummyResult(stdout='{"active_modes":["run","team"]}\n')

    monkeypatch.setattr(active_runtime_modes, "run_omx_command", fake_run)

    result = asyncio.run(active_runtime_modes.read_active_runtime_modes())

    assert result.active_modes == ("run", "team")
    assert seen_arguments == [["state", "list-active", "--json"]]


def test_load_active_runtime_modes_payload_rejects_non_object_transport() -> None:
    with pytest.raises(RuntimeSurfaceError):
        active_runtime_modes._load_active_runtime_modes_payload("[]")


def test_load_active_runtime_modes_payload_rejects_missing_active_modes_payload() -> None:
    with pytest.raises(RuntimeSurfaceError):
        active_runtime_modes._normalize_active_runtime_modes("{}")
