from typing import Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    CapabilitySupport,
    NativeCapability,
)


class NativeCapabilityState(StrictModel):
    capability: NativeCapability
    support: CapabilitySupport
    detail: NonEmptyString
    native_surfaces: tuple[NonEmptyString, ...] = ()


class ProviderReadiness(StrictModel):
    installed: bool
    authenticated: CapabilitySupport
    execution_ready: CapabilitySupport
    unavailable: bool
    detail: NonEmptyString


class ProviderCapabilityMatrix(StrictModel):
    provider: ProviderId
    binary: NonEmptyString
    resolved_path: NonEmptyString | None = None
    version: NonEmptyString | None = None
    readiness: ProviderReadiness
    capabilities: tuple[NativeCapabilityState, ...]
    native_features: tuple[NonEmptyString, ...] = ()


class CapabilityMatrixReport(StrictModel):
    schema_version: Literal["capability-matrix.v1"] = "capability-matrix.v1"
    providers: tuple[ProviderCapabilityMatrix, ...]
