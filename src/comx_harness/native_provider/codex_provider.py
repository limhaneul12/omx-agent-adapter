from pathlib import Path

from comx_harness.native_provider.provider_adapter import (
    NativeAuthenticationProbe,
    ProviderAdapter,
)
from comx_harness.schemas.execution_schemas import ExecutionPlan, ExecutionRequest
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import CapabilitySupport


class CodexProvider(ProviderAdapter):
    provider_id = ProviderId.CODEX
    binary_name = "codex"

    def _probe_authentication(self, resolved_path: str) -> NativeAuthenticationProbe:
        return self._probe_authentication_command(
            (resolved_path, "login", "status"),
            success_support=CapabilitySupport.SUPPORTED,
            success_detail="Codex reports an active local ChatGPT login.",
        )

    def build_run_argv(
        self, request: ExecutionRequest, result_path: Path
    ) -> tuple[str, ...]:
        binary = self.require_available()
        argv = (
            binary,
            "exec",
            *self._common_exec_options(request, result_path),
            request.objective,
        )
        return argv

    def build_resume_argv(
        self,
        plan: ExecutionPlan,
        session_id: str,
        objective: str,
        result_path: Path,
    ) -> tuple[str, ...]:
        binary = self.require_available()
        argv = (
            binary,
            "exec",
            "resume",
            *self._common_resume_options(plan, result_path),
            session_id,
            objective,
        )
        return argv

    def native_features(self) -> tuple[str, ...]:
        features = (
            "exec",
            "review",
            "mcp",
            "plugin",
            "sandbox",
            "resume",
            "fork",
            "cloud",
        )
        return features
