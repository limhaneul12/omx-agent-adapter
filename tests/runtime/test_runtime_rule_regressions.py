import asyncio
from unittest.mock import Mock

from omx_remote.runtime.status.runtime_snapshot import read_runtime_status
from omx_remote.schemas.runtime.status_schemas import RuntimeStatusRequest


def test_read_runtime_status_accepts_missing_request_without_or_fallback(monkeypatch) -> None:
    mock_result = Mock(stdout="No active modes.\n", stderr="")
    monkeypatch.setattr(
        "omx_remote.runtime.status.runtime_snapshot.run_omx_command",
        lambda arguments: mock_result,
    )

    result = asyncio.run(read_runtime_status())

    assert result.summary == "No active modes."
    assert result.has_active_modes is False


def test_read_runtime_status_accepts_explicit_request_object(monkeypatch) -> None:
    mock_result = Mock(stdout="No active modes.\n", stderr="")
    monkeypatch.setattr(
        "omx_remote.runtime.status.runtime_snapshot.run_omx_command",
        lambda arguments: mock_result,
    )

    result = asyncio.run(read_runtime_status(RuntimeStatusRequest()))

    assert result.summary == "No active modes."
