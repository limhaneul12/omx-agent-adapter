from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictSchemaModel,
)


class AdapterProbeRequest(StrictSchemaModel):
    """Represents the typed request boundary for adapt read-only probes."""

    target: NonEmptyString


class AdapterCapabilitySnapshot(StrictSchemaModel):
    """Represents one normalized adapter capability summary."""

    id: NonEmptyString
    label: NonEmptyString
    status: NonEmptyString
    summary: NonEmptyString
    ownership: NonEmptyString | None = None


class AdapterProbeSnapshot(StrictSchemaModel):
    """Represents the normalized result for `omx adapt <target> probe --json`."""

    target: NonEmptyString
    phase: NonEmptyString
    summary: NonEmptyString
    capabilities: tuple[AdapterCapabilitySnapshot, ...]
    target_runtime_state: NonEmptyString
    target_runtime_detail: NonEmptyString


class AdapterStatusSnapshot(StrictSchemaModel):
    """Represents the normalized result for `omx adapt <target> status --json`."""

    target: NonEmptyString
    phase: NonEmptyString
    summary: NonEmptyString
    adapter_state: NonEmptyString
    adapter_detail: NonEmptyString
    target_runtime_state: NonEmptyString
    target_runtime_detail: NonEmptyString
    capabilities: tuple[AdapterCapabilitySnapshot, ...]


class AdapterEnvelopeSnapshot(StrictSchemaModel):
    """Represents the normalized result for `omx adapt <target> envelope --json`."""

    target: NonEmptyString
    display_name: NonEmptyString
    summary: NonEmptyString
    capabilities: tuple[AdapterCapabilitySnapshot, ...]
    target_runtime_state: NonEmptyString
    target_runtime_detail: NonEmptyString
