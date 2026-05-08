import asyncio
import inspect

import pytest

from omx_remote.runtime.status import runtime_mode_status
from omx_remote.schemas.runtime.status_schemas import RuntimeModeStatusRequest
from omx_remote.shared.exceptions import RuntimeSurfaceError


class DummyResult:
    def __init__(self, stdout: str = "{}", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_runtime_mode_status_is_async() -> None:
    assert inspect.iscoroutinefunction(runtime_mode_status.read_runtime_mode_status)


def test_read_runtime_mode_status_returns_typed_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"statuses":{"ralph":{"active":true,"phase":"starting","path":"/tmp/ralph-state.json","data":{"current_phase":"starting","iteration":0}}}}\n'
        ),
    )

    result = asyncio.run(
        runtime_mode_status.read_runtime_mode_status(
            RuntimeModeStatusRequest(mode="ralph")
        )
    )

    assert result.requested_mode == "ralph"
    assert result.found is True
    assert result.mode_snapshot is not None
    assert result.mode_snapshot.name == "ralph"
    assert result.mode_snapshot.is_active is True
    assert result.mode_snapshot.phase == "starting"
    assert result.mode_snapshot.state_path == "/tmp/ralph-state.json"


def test_read_runtime_mode_status_returns_missing_result_for_unknown_mode(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"statuses":{}}\n'),
    )

    result = asyncio.run(
        runtime_mode_status.read_runtime_mode_status(
            RuntimeModeStatusRequest(mode="missing-mode")
        )
    )

    assert result.requested_mode == "missing-mode"
    assert result.found is False
    assert result.mode_snapshot is None


def test_read_runtime_mode_status_uses_nested_current_phase_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"statuses":{"ralph":{"active":true,"path":"/tmp/ralph-state.json","data":{"current_phase":"executing"}}}}\n'
        ),
    )

    result = asyncio.run(
        runtime_mode_status.read_runtime_mode_status(
            RuntimeModeStatusRequest(mode="ralph")
        )
    )

    assert result.mode_snapshot is not None
    assert result.mode_snapshot.phase == "executing"


def test_read_runtime_mode_status_treats_empty_phase_as_missing_for_nested_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(
            stdout='{"statuses":{"team":{"active":true,"phase":"","path":"","data":{"current_phase":"team-exec"}}}}\n'
        ),
    )

    result = asyncio.run(
        runtime_mode_status.read_runtime_mode_status(
            RuntimeModeStatusRequest(mode="team")
        )
    )

    assert result.mode_snapshot is not None
    assert result.mode_snapshot.phase == "team-exec"
    assert result.mode_snapshot.state_path is None


def test_read_runtime_mode_status_invokes_expected_state_command(monkeypatch) -> None:
    seen_arguments: list[list[str]] = []

    def fake_run(arguments: list[str]) -> DummyResult:
        seen_arguments.append(arguments)
        return DummyResult(stdout='{"statuses":{"team":{"active":true,"phase":"team-exec","path":"/tmp/team-state.json"}}}\n')

    monkeypatch.setattr(runtime_mode_status, "run_omx_command", fake_run)

    result = asyncio.run(
        runtime_mode_status.read_runtime_mode_status(
            RuntimeModeStatusRequest(mode="team")
        )
    )

    assert result.found is True
    assert seen_arguments == [
        [
            "state",
            "get-status",
            "--input",
            '{"mode":"team"}',
            "--json",
        ]
    ]


def test_read_runtime_mode_status_rejects_unparseable_json_transport(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(stdout="not-json\n"),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(
            runtime_mode_status.read_runtime_mode_status(
                RuntimeModeStatusRequest(mode="ralph")
            )
        )


def test_read_runtime_mode_status_rejects_non_mapping_transport(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='["ralph"]\n'),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(
            runtime_mode_status.read_runtime_mode_status(
                RuntimeModeStatusRequest(mode="ralph")
            )
        )


def test_read_runtime_mode_status_rejects_missing_active_field_in_status_entry(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_mode_status,
        "run_omx_command",
        lambda arguments: DummyResult(stdout='{"statuses":{"ralph":{}}}\n'),
    )

    with pytest.raises(RuntimeSurfaceError):
        asyncio.run(
            runtime_mode_status.read_runtime_mode_status(
                RuntimeModeStatusRequest(mode="ralph")
            )
        )


def test_load_runtime_mode_status_payload_rejects_non_object_statuses_payload() -> None:
    with pytest.raises(RuntimeSurfaceError):
        runtime_mode_status._normalize_runtime_mode_status(
            stdout='{"statuses":[]}',
            requested_mode="ralph",
        )


def test_load_runtime_mode_status_payload_rejects_non_string_phase_when_present() -> None:
    with pytest.raises(RuntimeSurfaceError):
        runtime_mode_status._load_runtime_mode_status_payload(
            '{"statuses":{"ralph":{"active":true,"phase":42}}}'
        )


def test_load_runtime_mode_status_payload_rejects_non_string_path_when_present() -> None:
    with pytest.raises(RuntimeSurfaceError):
        runtime_mode_status._load_runtime_mode_status_payload(
            '{"statuses":{"ralph":{"active":true,"path":42}}}'
        )


def test_load_runtime_mode_status_payload_rejects_non_string_current_phase_when_present() -> None:
    with pytest.raises(RuntimeSurfaceError):
        runtime_mode_status._load_runtime_mode_status_payload(
            '{"statuses":{"ralph":{"active":true,"data":{"current_phase":42}}}}'
        )
