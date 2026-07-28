from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.shared.harness_enums.provider_enums import Operation, ProviderId


class ProviderCapability(StrictModel):
    operation: Operation
    supported: bool
    native_command: tuple[NonEmptyString, ...] = ()
    detail: NonEmptyString


class ProviderInfo(StrictModel):
    provider: ProviderId
    binary: NonEmptyString
    available: bool
    resolved_path: NonEmptyString | None = None
    version: NonEmptyString | None = None
    capabilities: tuple[ProviderCapability, ...]
    native_features: tuple[NonEmptyString, ...] = ()


class CapabilityReport(StrictModel):
    providers: tuple[ProviderInfo, ...]
