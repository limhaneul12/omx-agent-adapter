from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omx_remote.schemas.common_schemas import NonEmptyString

RuntimeModeStatus = Literal["active", "paused", "idle", "unknown"]
RuntimeStatusAnomalyCategory = Literal[
    "stderr_fallback",
    "unknown_mode_status",
    "empty_transport_output",
    "unparseable_stdout",
]


class RuntimeStatusRequest(BaseModel):
    """Represents the typed request boundary for runtime status reads."""

    model_config = ConfigDict(extra="forbid")


class RuntimeModeStatusRequest(BaseModel):
    """Represents the typed request boundary for runtime mode-status reads."""

    model_config = ConfigDict(extra="forbid")

    mode: NonEmptyString


class ActiveRuntimeModes(BaseModel):
    """Represents the normalized active-runtime mode list."""

    model_config = ConfigDict(extra="forbid")

    active_modes: list[NonEmptyString] = Field(default_factory=list)


class RuntimeModeSnapshot(BaseModel):
    """Represents one normalized runtime mode status."""

    model_config = ConfigDict(extra="forbid")

    name: NonEmptyString
    status: RuntimeModeStatus
    raw_status_text: str | None = None
    has_uncertainty: bool = False


class RuntimeModeStatusSnapshot(BaseModel):
    """Represents one normalized runtime mode-status lookup result."""

    model_config = ConfigDict(extra="forbid")

    name: NonEmptyString
    is_active: bool
    phase: NonEmptyString | None = None
    state_path: NonEmptyString | None = None


class RuntimeModeStatusResult(BaseModel):
    """Represents the normalized public result for one runtime mode-status read."""

    model_config = ConfigDict(extra="forbid")

    requested_mode: NonEmptyString
    found: bool
    mode_snapshot: RuntimeModeStatusSnapshot | None = None

    @model_validator(mode="after")
    def _validate_mode_snapshot_presence(self) -> "RuntimeModeStatusResult":
        """Validates that found-state and snapshot presence stay aligned."""
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


class RuntimeStatusAnomaly(BaseModel):
    """Represents a normalized runtime-status anomaly."""

    model_config = ConfigDict(extra="forbid")

    category: RuntimeStatusAnomalyCategory
    message: str
    mode_name: NonEmptyString | None = None


class RuntimeStatus(BaseModel):
    """Represents normalized OMX runtime status output."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    has_active_modes: bool | None = None
    active_mode_names: list[NonEmptyString] = Field(default_factory=list)
    mode_snapshots: list[RuntimeModeSnapshot] = Field(default_factory=list)
    mode_statuses: dict[str, RuntimeModeStatus] = Field(default_factory=dict)
    anomalies: list[RuntimeStatusAnomaly] = Field(default_factory=list)
    has_anomalies: bool = False
    anomaly_count: int = 0
