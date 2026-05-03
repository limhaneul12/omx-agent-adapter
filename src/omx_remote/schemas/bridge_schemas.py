from pydantic import BaseModel, ConfigDict, Field

from omx_remote.schemas.common_schemas import NonEmptyString


class AdapterProbeRequest(BaseModel):
    """Represents the typed request boundary for adapt read-only probes."""

    model_config = ConfigDict(extra="forbid")

    target: NonEmptyString


class AdapterCapabilitySnapshot(BaseModel):
    """Represents one normalized adapter capability summary."""

    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    label: NonEmptyString
    status: NonEmptyString
    summary: NonEmptyString
    ownership: NonEmptyString | None = None


class AdapterProbeSnapshot(BaseModel):
    """Represents the normalized result for `omx adapt <target> probe --json`."""

    model_config = ConfigDict(extra="forbid")

    target: NonEmptyString
    phase: NonEmptyString
    summary: NonEmptyString
    capabilities: list[AdapterCapabilitySnapshot] = Field(default_factory=list)
    target_runtime_state: NonEmptyString
    target_runtime_detail: NonEmptyString


class AdapterStatusSnapshot(BaseModel):
    """Represents the normalized result for `omx adapt <target> status --json`."""

    model_config = ConfigDict(extra="forbid")

    target: NonEmptyString
    phase: NonEmptyString
    summary: NonEmptyString
    adapter_state: NonEmptyString
    adapter_detail: NonEmptyString
    target_runtime_state: NonEmptyString
    target_runtime_detail: NonEmptyString
    capabilities: list[AdapterCapabilitySnapshot] = Field(default_factory=list)


class AdapterEnvelopeSnapshot(BaseModel):
    """Represents the normalized result for `omx adapt <target> envelope --json`."""

    model_config = ConfigDict(extra="forbid")

    target: NonEmptyString
    display_name: NonEmptyString
    summary: NonEmptyString
    capabilities: list[AdapterCapabilitySnapshot] = Field(default_factory=list)
    target_runtime_state: NonEmptyString
    target_runtime_detail: NonEmptyString
