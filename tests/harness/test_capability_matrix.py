from comx_harness.application.capability_matrix import (
    capability_support,
    resolve_capability_matrix,
)
from comx_harness.schemas.provider_schemas import (
    CapabilityReport,
    ProviderCapability,
    ProviderInfo,
)
from comx_harness.shared.harness_enums.provider_enums import Operation, ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    CapabilitySupport,
    NativeCapability,
)


def test_capability_matrix_distinguishes_installed_from_execution_ready() -> None:
    report = CapabilityReport(
        providers=(
            ProviderInfo(
                provider=ProviderId.CODEX,
                binary="codex",
                available=True,
                resolved_path="/usr/local/bin/codex",
                version="codex 1.0",
                capabilities=(
                    ProviderCapability(
                        operation=Operation.RUN,
                        supported=True,
                        detail="parser accepted",
                    ),
                    ProviderCapability(
                        operation=Operation.CANCEL,
                        supported=True,
                        detail="bounded cancellation",
                    ),
                    ProviderCapability(
                        operation=Operation.RESUME,
                        supported=True,
                        detail="native resume",
                    ),
                ),
                native_features=("exec", "resume"),
            ),
            ProviderInfo(
                provider=ProviderId.OMX,
                binary="omx",
                available=False,
                capabilities=(
                    ProviderCapability(
                        operation=Operation.RUN,
                        supported=False,
                        detail="not installed",
                    ),
                ),
            ),
        )
    )

    matrix = resolve_capability_matrix(report)
    codex = matrix.providers[0]
    omx = matrix.providers[1]

    assert codex.readiness.installed is True
    assert codex.readiness.authenticated == CapabilitySupport.UNKNOWN
    assert codex.readiness.execution_ready == CapabilitySupport.CONDITIONAL
    assert codex.readiness.unavailable is False
    assert omx.readiness.installed is False
    assert omx.readiness.execution_ready == CapabilitySupport.UNSUPPORTED
    assert omx.readiness.unavailable is True


def test_capability_matrix_keeps_native_ownership_explicit() -> None:
    report = CapabilityReport(
        providers=(
            ProviderInfo(
                provider=ProviderId.CODEX,
                binary="codex",
                available=True,
                resolved_path="/bin/codex",
                capabilities=(
                    ProviderCapability(
                        operation=Operation.RUN,
                        supported=True,
                        detail="ready",
                    ),
                ),
                native_features=("exec",),
            ),
            ProviderInfo(
                provider=ProviderId.OMX,
                binary="omx",
                available=True,
                resolved_path="/bin/omx",
                capabilities=(
                    ProviderCapability(
                        operation=Operation.RUN,
                        supported=True,
                        detail="ready",
                    ),
                ),
                native_features=("exec", "team", "ralph", "ultragoal"),
            ),
        )
    )

    matrix = resolve_capability_matrix(report)

    assert (
        capability_support(matrix, ProviderId.CODEX, NativeCapability.NATIVE_TEAM)
        == CapabilitySupport.UNSUPPORTED
    )
    assert (
        capability_support(
            matrix, ProviderId.CODEX, NativeCapability.STRUCTURED_SUBAGENTS
        )
        == CapabilitySupport.UNKNOWN
    )
    assert (
        capability_support(matrix, ProviderId.OMX, NativeCapability.NATIVE_TEAM)
        == CapabilitySupport.CONDITIONAL
    )
    assert (
        capability_support(matrix, ProviderId.OMX, NativeCapability.NATIVE_LOOP)
        == CapabilitySupport.CONDITIONAL
    )
    assert (
        capability_support(matrix, ProviderId.OMX, NativeCapability.PARALLEL_WORKERS)
        == CapabilitySupport.CONDITIONAL
    )
