from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    active_mode_names: list[str] = Field(default_factory=list)
    mode_snapshots: list[RuntimeModeSnapshot] = Field(default_factory=list)
    mode_statuses: dict[str, RuntimeModeStatus] = Field(default_factory=dict)
    anomalies: list[RuntimeStatusAnomaly] = Field(default_factory=list)
    has_anomalies: bool = False
    anomaly_count: int = 0
