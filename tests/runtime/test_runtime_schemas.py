import pytest
from pydantic import ValidationError

from omx_remote.schemas.runtime_schemas import (
    ActiveRuntimeModes,
    RuntimeModeSnapshot,
    RuntimeModeStatusRequest,
    RuntimeModeStatusResult,
    RuntimeModeStatusSnapshot,
    RuntimeStatus,
    RuntimeStatusAnomaly,
    RuntimeStatusRequest,
)


def test_runtime_status_request_accepts_empty_input() -> None:
    result = RuntimeStatusRequest.model_validate({})

    assert result == RuntimeStatusRequest()


def test_runtime_status_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeStatusRequest.model_validate({"unexpected": True})


def test_runtime_mode_status_request_requires_mode() -> None:
    result = RuntimeModeStatusRequest.model_validate({"mode": "ralph"})

    assert result.mode == "ralph"


def test_runtime_mode_status_request_rejects_unexpected_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeModeStatusRequest.model_validate({"mode": "ralph", "unexpected": True})


def test_runtime_mode_snapshot_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        RuntimeModeSnapshot(name="", status="active")


def test_runtime_mode_status_snapshot_rejects_empty_state_path() -> None:
    with pytest.raises(ValidationError):
        RuntimeModeStatusSnapshot(
            name="ralph",
            is_active=True,
            state_path="",
        )


def test_runtime_mode_status_result_requires_snapshot_when_found() -> None:
    with pytest.raises(ValidationError):
        RuntimeModeStatusResult.model_validate(
            {
                "requested_mode": "ralph",
                "found": True,
                "mode_snapshot": None,
            }
        )


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


def test_runtime_status_rejects_empty_active_mode_name_entries() -> None:
    with pytest.raises(ValidationError):
        RuntimeStatus.model_validate(
            {
                "summary": "ralph: active",
                "active_mode_names": ["ralph", ""],
                "mode_snapshots": [],
                "mode_statuses": {"ralph": "active"},
                "anomalies": [],
                "has_anomalies": False,
                "anomaly_count": 0,
            }
        )
