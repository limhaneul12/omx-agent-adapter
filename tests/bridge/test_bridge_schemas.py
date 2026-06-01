import pytest
from pydantic import ValidationError

from omx_remote.schemas.bridge_adapter_schemas import (
    AdapterCapabilitySnapshot,
    AdapterEnvelopeSnapshot,
    AdapterProbeRequest,
    AdapterProbeSnapshot,
    AdapterStatusSnapshot,
)


def test_adapter_probe_request_accepts_target() -> None:
    result = AdapterProbeRequest.model_validate({"target": "hermes"})

    assert result.target == "hermes"


def test_adapter_probe_request_rejects_empty_target() -> None:
    with pytest.raises(ValidationError):
        AdapterProbeRequest.model_validate({"target": ""})


def test_adapter_probe_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AdapterProbeRequest.model_validate({"target": "hermes", "unexpected": True})


def test_adapter_capability_snapshot_accepts_minimal_fields() -> None:
    result = AdapterCapabilitySnapshot.model_validate(
        {
            "id": "foundation-reporting",
            "label": "Foundation reporting surface",
            "status": "ready",
            "summary": "Probe, status, and envelope share a contract.",
        }
    )

    assert result.id == "foundation-reporting"
    assert result.status == "ready"


def test_adapter_probe_snapshot_accepts_live_probe_subset() -> None:
    result = AdapterProbeSnapshot.model_validate(
        {
            "target": "hermes",
            "phase": "foundation",
            "summary": "Hermes probe inspected runtime evidence.",
            "capabilities": [
                {
                    "id": "foundation-reporting",
                    "label": "Foundation reporting surface",
                    "status": "ready",
                    "summary": "Probe, status, and envelope share a contract.",
                }
            ],
            "target_runtime_state": "unavailable",
            "target_runtime_detail": "Hermes runtime missing.",
        }
    )

    assert result.target == "hermes"
    assert result.phase == "foundation"
    assert isinstance(result.capabilities, tuple)
    assert len(result.capabilities) == 1
    assert result.target_runtime_state == "unavailable"


def test_adapter_status_snapshot_accepts_live_status_subset() -> None:
    result = AdapterStatusSnapshot.model_validate(
        {
            "target": "hermes",
            "phase": "foundation",
            "summary": "Adapter is not initialized yet.",
            "adapter_state": "not-initialized",
            "adapter_detail": "Run init --write.",
            "target_runtime_state": "unavailable",
            "target_runtime_detail": "Hermes runtime missing.",
            "capabilities": [],
        }
    )

    assert result.adapter_state == "not-initialized"
    assert result.capabilities == ()
    assert result.target_runtime_state == "unavailable"


def test_adapter_envelope_snapshot_accepts_live_envelope_subset() -> None:
    result = AdapterEnvelopeSnapshot.model_validate(
        {
            "target": "hermes",
            "display_name": "Hermes",
            "summary": "Foundation seam for Hermes.",
            "capabilities": [],
            "target_runtime_state": "unavailable",
            "target_runtime_detail": "Hermes runtime missing.",
        }
    )

    assert result.display_name == "Hermes"
    assert result.capabilities == ()
    assert result.target_runtime_state == "unavailable"
