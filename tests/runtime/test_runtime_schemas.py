import pytest
from pydantic import ValidationError

from omx_remote.schemas.runtime_schemas import (
    ActiveRuntimeModes,
    RuntimeModeSnapshot,
    RuntimeStatusAnomaly,
    RuntimeStatusRequest,
)


def test_runtime_status_request_accepts_empty_input() -> None:
    result = RuntimeStatusRequest.model_validate({})

    assert result == RuntimeStatusRequest()


def test_runtime_status_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeStatusRequest.model_validate({"unexpected": True})


def test_runtime_mode_snapshot_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        RuntimeModeSnapshot(name="", status="active")


def test_runtime_status_anomaly_rejects_empty_mode_name_when_present() -> None:
    with pytest.raises(ValidationError):
        RuntimeStatusAnomaly(
            category="unknown_mode_status",
            message="spinning",
            mode_name="",
        )


def test_active_runtime_modes_accepts_non_empty_mode_names() -> None:
    result = ActiveRuntimeModes.model_validate({"active_modes": ["ralph", "run"]})

    assert result.active_modes == ["ralph", "run"]


def test_active_runtime_modes_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ActiveRuntimeModes.model_validate(
            {"active_modes": ["ralph"], "unexpected": True}
        )


def test_active_runtime_modes_rejects_empty_mode_name_entries() -> None:
    with pytest.raises(ValidationError):
        ActiveRuntimeModes.model_validate({"active_modes": ["ralph", ""]})
