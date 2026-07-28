from typing import Final

from comx_harness.native_provider.codex_provider import CodexProvider
from comx_harness.native_provider.omx_provider import OmxProvider
from comx_harness.native_provider.provider_adapter import ProviderAdapter
from comx_harness.schemas.provider_schemas import CapabilityReport
from comx_harness.shared.harness_enums.provider_enums import ProviderId

_PROVIDER_TYPES: Final[dict[ProviderId, type[ProviderAdapter]]] = {
    ProviderId.CODEX: CodexProvider,
    ProviderId.OMX: OmxProvider,
}


class ProviderRegistry:
    """Small runtime provider registry shared by every controller adapter."""

    def get(self, provider_id: ProviderId | str) -> ProviderAdapter:
        normalized = ProviderId(provider_id)
        provider_type = _PROVIDER_TYPES[normalized]
        provider = provider_type()
        return provider

    def discover(self) -> CapabilityReport:
        providers = tuple(
            self.get(provider_id).discover() for provider_id in ProviderId
        )
        report = CapabilityReport(providers=providers)
        return report
