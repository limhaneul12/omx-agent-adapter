from __future__ import annotations

from comx_harness.schemas.capability_matrix_schemas import (
    CapabilityMatrixReport,
    NativeCapabilityState,
    ProviderCapabilityMatrix,
    ProviderReadiness,
)
from comx_harness.schemas.provider_schemas import CapabilityReport, ProviderInfo
from comx_harness.shared.harness_enums.provider_enums import Operation, ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    CapabilitySupport,
    NativeCapability,
)


def resolve_capability_matrix(report: CapabilityReport) -> CapabilityMatrixReport:
    providers = tuple(_resolve_provider(info) for info in report.providers)
    return CapabilityMatrixReport(providers=providers)


def capability_support(
    report: CapabilityMatrixReport,
    provider: ProviderId,
    capability: NativeCapability,
) -> CapabilitySupport:
    for provider_matrix in report.providers:
        if ProviderId(provider_matrix.provider) != provider:
            continue
        for state in provider_matrix.capabilities:
            if NativeCapability(state.capability) == capability:
                return CapabilitySupport(state.support)
    return CapabilitySupport.UNKNOWN


def _resolve_provider(info: ProviderInfo) -> ProviderCapabilityMatrix:
    provider = ProviderId(info.provider)
    run_supported = _operation_supported(info, Operation.RUN)
    installed = bool(info.available and info.resolved_path is not None)
    execution_ready = (
        CapabilitySupport.CONDITIONAL
        if run_supported and info.authentication != CapabilitySupport.UNSUPPORTED
        else CapabilitySupport.UNSUPPORTED
    )
    unavailable = (
        not installed
        or not run_supported
        or info.authentication == CapabilitySupport.UNSUPPORTED
    )
    if not installed:
        detail = f"{info.binary} is not installed"
    elif not run_supported:
        detail = (
            f"{info.binary} is installed but its native execution contract is "
            "not compatible"
        )
    elif info.authentication == CapabilitySupport.UNSUPPORTED:
        detail = info.authentication_detail
    else:
        detail = (
            f"{info.binary} accepts the native parser contract. "
            f"{info.authentication_detail} Live read-only execution remains unverified."
        )
    readiness = ProviderReadiness(
        installed=installed,
        authenticated=info.authentication,
        execution_ready=execution_ready,
        unavailable=unavailable,
        detail=detail,
    )
    capabilities = tuple(
        _native_capability_state(info, capability) for capability in NativeCapability
    )
    return ProviderCapabilityMatrix(
        provider=provider,
        binary=info.binary,
        resolved_path=info.resolved_path,
        version=info.version,
        readiness=readiness,
        capabilities=capabilities,
        native_features=info.native_features,
    )


def _native_capability_state(
    info: ProviderInfo,
    capability: NativeCapability,
) -> NativeCapabilityState:
    provider = ProviderId(info.provider)
    run_supported = _operation_supported(info, Operation.RUN)
    features = set(info.native_features)
    conditional = (
        CapabilitySupport.CONDITIONAL
        if run_supported
        else CapabilitySupport.UNSUPPORTED
    )

    if capability == NativeCapability.DETACHED_EXECUTION:
        return NativeCapabilityState(
            capability=capability,
            support=conditional,
            detail=(
                "The platform can detach a native Run, subject to live provider "
                "authentication."
                if run_supported
                else "Detached execution requires a compatible native Run contract."
            ),
            native_surfaces=("exec",),
        )
    if capability == NativeCapability.CANCELLATION:
        supported = _operation_supported(info, Operation.CANCEL)
        return NativeCapabilityState(
            capability=capability,
            support=(
                CapabilitySupport.CONDITIONAL
                if supported
                else CapabilitySupport.UNSUPPORTED
            ),
            detail=(
                "Bounded process-group cancellation is available after a Run starts."
                if supported
                else "The provider cannot start a cancellable native Run."
            ),
        )
    if capability == NativeCapability.RESUME:
        supported = _operation_supported(info, Operation.RESUME)
        return NativeCapabilityState(
            capability=capability,
            support=(
                CapabilitySupport.CONDITIONAL
                if supported
                else CapabilitySupport.UNSUPPORTED
            ),
            detail=(
                "Resume requires an observed native session identifier."
                if supported
                else "The native resume contract is unavailable."
            ),
            native_surfaces=("exec resume",) if supported else (),
        )
    if capability == NativeCapability.INTERACTIVE_INPUT:
        return NativeCapabilityState(
            capability=capability,
            support=CapabilitySupport.UNSUPPORTED,
            detail="The first Strategy slice supports non-interactive native Runs only.",
        )
    if capability == NativeCapability.STRUCTURED_EVENTS:
        return NativeCapabilityState(
            capability=capability,
            support=conditional,
            detail=(
                "Native JSONL output is normalized into durable Run events."
                if run_supported
                else "Structured events require a compatible native Run contract."
            ),
            native_surfaces=("exec --json",) if run_supported else (),
        )
    if capability == NativeCapability.STRUCTURED_SUBAGENTS:
        if provider == ProviderId.OMX and "team" in features:
            return NativeCapabilityState(
                capability=capability,
                support=CapabilitySupport.CONDITIONAL,
                detail=(
                    "OMX Team workers and tasks are visible only when native JSON "
                    "observation surfaces report them."
                ),
                native_surfaces=("team status", "team list-tasks"),
            )
        return NativeCapabilityState(
            capability=capability,
            support=(
                CapabilitySupport.UNKNOWN
                if provider == ProviderId.CODEX
                else CapabilitySupport.UNSUPPORTED
            ),
            detail=(
                "Codex structured subagent topology is not exposed by the current "
                "native contract."
                if provider == ProviderId.CODEX
                else "No structured native subagent surface was discovered."
            ),
        )
    if capability == NativeCapability.ARTIFACTS:
        return NativeCapabilityState(
            capability=capability,
            support=CapabilitySupport.SUPPORTED,
            detail="The harness verifies result, logs, events, and declared files.",
        )
    if capability == NativeCapability.NATIVE_TEAM:
        supported = provider == ProviderId.OMX and "team" in features
        return NativeCapabilityState(
            capability=capability,
            support=(
                CapabilitySupport.CONDITIONAL
                if supported
                else CapabilitySupport.UNSUPPORTED
            ),
            detail=(
                "OMX owns Team scheduling; the platform launches and observes it."
                if supported
                else "No provider-native Team surface is available."
            ),
            native_surfaces=("team",) if supported else (),
        )
    if capability == NativeCapability.NATIVE_LOOP:
        surfaces = tuple(
            feature
            for feature in ("ralph", "ultragoal", "ralplan")
            if feature in features
        )
        return NativeCapabilityState(
            capability=capability,
            support=(
                CapabilitySupport.CONDITIONAL
                if surfaces
                else CapabilitySupport.UNSUPPORTED
            ),
            detail=(
                "OMX owns bounded native loop workflows."
                if surfaces
                else "No provider-native bounded loop surface was discovered."
            ),
            native_surfaces=surfaces,
        )
    if capability == NativeCapability.PARALLEL_WORKERS:
        if provider == ProviderId.OMX and "team" in features:
            return NativeCapabilityState(
                capability=capability,
                support=CapabilitySupport.CONDITIONAL,
                detail="Parallel workers remain owned by the OMX Team runtime.",
                native_surfaces=("team",),
            )
        return NativeCapabilityState(
            capability=capability,
            support=CapabilitySupport.UNKNOWN,
            detail=(
                "No structured native evidence proves independently controllable "
                "parallel workers."
            ),
        )
    raise AssertionError(f"unhandled native capability: {capability}")


def _operation_supported(info: ProviderInfo, operation: Operation) -> bool:
    for capability in info.capabilities:
        if Operation(capability.operation) == operation:
            return capability.supported
    return False
