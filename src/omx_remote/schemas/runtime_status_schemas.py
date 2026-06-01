from pydantic import Field, model_validator

from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.shared.omx_enums.runtime_enums import (
    RuntimeModeStatus,
    RuntimeStatusAnomalyCategory,
)


class RuntimeStatusRequest(StrictSchemaModel):
    """Represents the typed request boundary for runtime status reads."""


class RuntimeModeStatusRequest(StrictSchemaModel):
    """Represents the typed request boundary for runtime mode-status reads."""

    mode: NonEmptyString


class RuntimeModeStateRequest(StrictSchemaModel):
    """Represents the typed request boundary for runtime mode-state reads."""

    mode: NonEmptyString


class ActiveRuntimeModes(StrictSchemaModel):
    """Represents the normalized active-runtime mode list."""

    active_modes: tuple[NonEmptyString, ...]


class RuntimeModeStateSnapshot(StrictSchemaModel):
    """Represents one normalized runtime mode-state lookup result."""

    mode: NonEmptyString
    exists: bool
    state: JsonObject | None = None


class RuntimeModeSnapshot(StrictSchemaModel):
    """Represents one normalized runtime mode status."""

    name: NonEmptyString
    status: RuntimeModeStatus
    raw_status_text: str | None = None
    has_uncertainty: bool = False


class RuntimeModeStatusSnapshot(StrictSchemaModel):
    """Represents one normalized runtime mode-status lookup result."""

    name: NonEmptyString
    is_active: bool
    phase: NonEmptyString | None = None
    state_path: NonEmptyString | None = None


class RuntimeModeStatusResult(StrictSchemaModel):
    """Represents the normalized public result for one runtime mode-status read."""

    requested_mode: NonEmptyString
    found: bool
    mode_snapshot: RuntimeModeStatusSnapshot | None = None

    @model_validator(mode="after")
    def _validate_mode_snapshot_presence(self) -> "RuntimeModeStatusResult":
        """Validates that found-state and snapshot presence stay aligned.

        Returns:
            'RuntimeModeStatusResult': Function return value.
        """
        if self.found and self.mode_snapshot is None:
            raise ValueError(
                "RuntimeModeStatusResult.mode_snapshot is required when found is true"
            )
        if not self.found and self.mode_snapshot is not None:
            raise ValueError(
                "RuntimeModeStatusResult.mode_snapshot must be absent when found is false"
            )
        validated_result: RuntimeModeStatusResult = self
        return validated_result


class RuntimeModeStateResult(StrictSchemaModel):
    """Represents the normalized public result for one runtime mode-state read."""

    mode: NonEmptyString
    exists: bool
    state: JsonObject | None = None

    @model_validator(mode="after")
    def _validate_state_presence(self) -> "RuntimeModeStateResult":
        """Validates that exists-state and payload presence stay aligned.

        Returns:
            'RuntimeModeStateResult': Function return value.
        """
        if self.exists and self.state is None:
            raise ValueError(
                "RuntimeModeStateResult.state is required when exists is true"
            )
        if not self.exists and self.state is not None:
            raise ValueError(
                "RuntimeModeStateResult.state must be absent when exists is false"
            )
        validated_result: RuntimeModeStateResult = self
        return validated_result


class RuntimeStatusAnomaly(StrictSchemaModel):
    """Represents a normalized runtime-status anomaly."""

    category: RuntimeStatusAnomalyCategory
    message: str
    mode_name: NonEmptyString | None = None


class RuntimeStatus(StrictSchemaModel):
    """Represents normalized OMX runtime status output."""

    summary: str
    has_active_modes: bool | None = None
    active_mode_names: tuple[NonEmptyString, ...]
    mode_snapshots: tuple[RuntimeModeSnapshot, ...]
    mode_statuses: dict[str, RuntimeModeStatus] = Field(default_factory=dict)
    anomalies: tuple[RuntimeStatusAnomaly, ...]
    has_anomalies: bool = False
    anomaly_count: int = 0
