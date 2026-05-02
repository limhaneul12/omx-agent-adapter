from typing import Literal

from pydantic import ConfigDict, Field

from schemas.common_schemas import AdapterSchema

RuntimeModeStatus = Literal["active", "paused", "idle", "unknown"]
RuntimeStatusAnomalyCategory = Literal[
    "stderr_fallback",
    "unknown_mode_status",
    "empty_transport_output",
    "unparseable_stdout",
]


class RuntimeModeSnapshot(AdapterSchema):
    """Represents one normalized runtime mode status."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: RuntimeModeStatus
    raw_status_text: str | None = None
    has_uncertainty: bool = False


class RuntimeStatusAnomaly(AdapterSchema):
    """Represents a normalized runtime-status anomaly."""

    model_config = ConfigDict(extra="forbid")

    category: RuntimeStatusAnomalyCategory
    message: str
    mode_name: str | None = None


class RuntimeStatus(AdapterSchema):
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
