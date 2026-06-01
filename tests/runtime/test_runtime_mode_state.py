import asyncio
import inspect

import pytest

from omx_remote.runtime.status import runtime_mode_state
from omx_remote.schemas.runtime_status_schemas import RuntimeModeStateRequest
from omx_remote.shared.exceptions import RuntimeSurfaceError


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_runtime_mode_state_is_async() -> None:
    assert inspect.iscoroutinefunction(runtime_mode_state.read_runtime_mode_state)


def test_read_runtime_mode_state_returns_missing_state_result(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_mode_state,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"exists":false,"mode":"team"}\n'),
    )

    result = asyncio.run(
        runtime_mode_state.read_runtime_mode_state(RuntimeModeStateRequest(mode="team"))
    )

    assert result.mode == "team"
    assert result.exists is False
    assert result.state is None


def test_read_runtime_mode_state_returns_present_state_result(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_mode_state,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"exists":true,"mode":"ralph","state":{"active":true,"current_phase":"executing"}}\n'
        ),
    )

    result = asyncio.run(
        runtime_mode_state.read_runtime_mode_state(
            RuntimeModeStateRequest(mode="ralph")
        )
    )

    assert result.mode == "ralph"
    assert result.exists is True
    assert result.state == {"active": True, "current_phase": "executing"}


def test_read_runtime_mode_state_accepts_direct_omx_state_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_mode_state,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"active":false,"mode":"ralph","current_phase":"cancelled"}\n'
        ),
    )

    result = asyncio.run(
        runtime_mode_state.read_runtime_mode_state(
            RuntimeModeStateRequest(mode="ralph")
        )
    )

    assert result.mode == "ralph"
    assert result.exists is True
    assert result.state == {
        "active": False,
        "mode": "ralph",
        "current_phase": "cancelled",
    }


def test_read_runtime_mode_state_rejects_unparseable_json_transport(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_mode_state,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(
            runtime_mode_state.read_runtime_mode_state(
                RuntimeModeStateRequest(mode="ralph")
            )
        )


def test_read_runtime_mode_state_rejects_non_object_state_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_mode_state,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"exists":true,"mode":"ralph","state":[]}\n'
        ),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(
            runtime_mode_state.read_runtime_mode_state(
                RuntimeModeStateRequest(mode="ralph")
            )
        )


def test_runtime_mode_state_payload_copy_preserves_dynamic_values() -> None:
    result = runtime_mode_state._copy_runtime_mode_state_payload(
        {
            "active": True,
            "count": 2,
            "nested": {"phase": "executing"},
            "warnings": ["slow"],
        }
    )

    assert result == {
        "active": True,
        "count": 2,
        "nested": {"phase": "executing"},
        "warnings": ["slow"],
    }


def test_runtime_mode_state_payload_copy_rejects_non_string_keys() -> None:
    with pytest.raises(RuntimeSurfaceError):
        runtime_mode_state._copy_runtime_mode_state_payload({1: "bad-key"})
