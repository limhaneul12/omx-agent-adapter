from typing import Literal

from pydantic import ConfigDict, Field

from schemas.common_schemas import AdapterSchema

RuntimeModeStatus = Literal["active", "paused", "idle", "unknown"]


class RuntimeStatus(AdapterSchema):
    model_config = ConfigDict(extra="forbid")

    summary: str
    has_active_modes: bool | None = None
    active_mode_names: list[str] = Field(default_factory=list)
    mode_statuses: dict[str, RuntimeModeStatus] = Field(default_factory=dict)
