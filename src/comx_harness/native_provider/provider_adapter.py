from __future__ import annotations

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from comx_harness.schemas.execution_schemas import ExecutionPlan, ExecutionRequest
from comx_harness.schemas.provider_schemas import ProviderCapability, ProviderInfo
from comx_harness.shared.exceptions.provider_exceptions import ProviderUnavailableError
from comx_harness.shared.harness_enums.execution_enums import SandboxMode
from comx_harness.shared.harness_enums.provider_enums import Operation, ProviderId
from comx_harness.shared.harness_enums.strategy_enums import CapabilitySupport


@dataclass(frozen=True, slots=True)
class NativeContractProbe:
    compatible: bool
    detail: str


@dataclass(frozen=True, slots=True)
class NativeAuthenticationProbe:
    support: CapabilitySupport
    detail: str


class ProviderAdapter(ABC):
    """Typed boundary around one native runtime provider."""

    provider_id: ProviderId
    binary_name: str

    def discover(self) -> ProviderInfo:
        resolved_path = shutil.which(self.binary_name)
        available = resolved_path is not None
        version = self._version(resolved_path) if resolved_path is not None else None
        contract_probe = (
            self._probe_native_contract(resolved_path)
            if resolved_path is not None
            else NativeContractProbe(
                compatible=False,
                detail=f"{self.binary_name} binary is not installed",
            )
        )
        authentication_probe = (
            self._probe_authentication(resolved_path)
            if resolved_path is not None
            else NativeAuthenticationProbe(
                support=CapabilitySupport.UNSUPPORTED,
                detail=f"{self.binary_name} binary is not installed",
            )
        )
        capabilities = self._capabilities(
            available=available,
            contract_probe=contract_probe,
        )
        info = ProviderInfo(
            provider=self.provider_id,
            binary=self.binary_name,
            available=available,
            resolved_path=resolved_path,
            version=version,
            authentication=authentication_probe.support,
            authentication_detail=authentication_probe.detail,
            capabilities=capabilities,
            native_features=self.native_features(),
        )
        return info

    def require_available(self) -> str:
        resolved_path = shutil.which(self.binary_name)
        if resolved_path is None:
            raise ProviderUnavailableError(
                f"provider {self.provider_id} is unavailable: {self.binary_name} not found"
            )
        contract_probe = self._probe_native_contract(resolved_path)
        if not contract_probe.compatible:
            raise ProviderUnavailableError(
                f"provider {self.provider_id} is incompatible: {contract_probe.detail}"
            )
        return resolved_path

    @abstractmethod
    def build_run_argv(
        self,
        request: ExecutionRequest,
        result_path: Path,
    ) -> tuple[str, ...]:
        """Build a native direct-execution argv."""

    @abstractmethod
    def build_resume_argv(
        self,
        plan: ExecutionPlan,
        session_id: str,
        objective: str,
        result_path: Path,
    ) -> tuple[str, ...]:
        """Build a native resume argv."""

    @abstractmethod
    def native_features(self) -> tuple[str, ...]:
        """Return meaningful provider-specific capability names."""

    def _probe_authentication(self, resolved_path: str) -> NativeAuthenticationProbe:
        del resolved_path
        return NativeAuthenticationProbe(
            support=CapabilitySupport.UNKNOWN,
            detail="The provider does not expose a safe local authentication probe.",
        )

    def _probe_authentication_command(
        self,
        argv: tuple[str, ...],
        *,
        success_support: CapabilitySupport,
        success_detail: str,
    ) -> NativeAuthenticationProbe:
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return NativeAuthenticationProbe(
                support=CapabilitySupport.UNKNOWN,
                detail=f"Authentication probe failed: {type(error).__name__}",
            )
        output = " ".join(
            line.strip()
            for line in (completed.stdout, completed.stderr)
            if line.strip()
        )
        if completed.returncode == 0:
            return NativeAuthenticationProbe(
                support=success_support,
                detail=success_detail,
            )
        detail = output[:240] or f"authentication command exited {completed.returncode}"
        return NativeAuthenticationProbe(
            support=CapabilitySupport.UNSUPPORTED,
            detail=detail,
        )

    def _capabilities(
        self,
        *,
        available: bool,
        contract_probe: NativeContractProbe,
    ) -> tuple[ProviderCapability, ...]:
        run_supported = available and contract_probe.compatible
        unavailable_detail = contract_probe.detail
        capabilities = (
            ProviderCapability(
                operation=Operation.CAPABILITIES,
                supported=True,
                native_command=(self.binary_name, "--help"),
                detail="Harness discovery is available even when the binary is missing.",
            ),
            ProviderCapability(
                operation=Operation.PLAN,
                supported=run_supported,
                native_command=(self.binary_name, "exec"),
                detail=(
                    "Preview the exact native argv without launching it."
                    if run_supported
                    else unavailable_detail
                ),
            ),
            ProviderCapability(
                operation=Operation.RUN,
                supported=run_supported,
                native_command=(self.binary_name, "exec", "--json"),
                detail=(
                    "Native non-interactive execution with JSONL events."
                    if run_supported
                    else unavailable_detail
                ),
            ),
            ProviderCapability(
                operation=Operation.HANDOFF,
                supported=run_supported,
                native_command=(self.binary_name, "exec", "--json"),
                detail=(
                    "Consumes a verified artifact through a new native run."
                    if run_supported
                    else unavailable_detail
                ),
            ),
            ProviderCapability(
                operation=Operation.STATUS,
                supported=True,
                detail="Normalized harness-owned run state and process liveness.",
            ),
            ProviderCapability(
                operation=Operation.EVENTS,
                supported=True,
                detail="Normalized events persisted from native JSONL output.",
            ),
            ProviderCapability(
                operation=Operation.CANCEL,
                supported=run_supported,
                detail=(
                    "Bounded cancellation of the recorded native process."
                    if run_supported
                    else unavailable_detail
                ),
            ),
            ProviderCapability(
                operation=Operation.RESUME,
                supported=run_supported,
                native_command=(self.binary_name, "exec", "resume"),
                detail=(
                    "Native session resume when a session id was observed."
                    if run_supported
                    else unavailable_detail
                ),
            ),
            ProviderCapability(
                operation=Operation.ARTIFACTS,
                supported=True,
                detail="Harness verification of result, logs, events, and declared artifacts.",
            ),
        )
        return capabilities

    def _probe_native_contract(self, resolved_path: str) -> NativeContractProbe:
        commands = (
            (
                "direct execution",
                (
                    resolved_path,
                    "exec",
                    "--json",
                    "-C",
                    ".",
                    "-o",
                    os.devnull,
                    "-c",
                    'approval_policy="never"',
                    "-c",
                    'web_search="live"',
                    "-s",
                    "read-only",
                    "--ephemeral",
                    "--help",
                ),
            ),
            (
                "resume",
                (
                    resolved_path,
                    "exec",
                    "resume",
                    "--json",
                    "-o",
                    os.devnull,
                    "-c",
                    'approval_policy="never"',
                    "-c",
                    'web_search="live"',
                    "--ephemeral",
                    "--help",
                ),
            ),
        )
        for operation, argv in commands:
            result = self._run_probe(argv)
            if result.returncode != 0:
                diagnostic = self._probe_diagnostic(result)
                return NativeContractProbe(
                    compatible=False,
                    detail=f"{operation} parser rejected the harness contract: {diagnostic}",
                )
        return NativeContractProbe(
            compatible=True,
            detail="native direct and resume argument contracts accepted",
        )

    def _run_probe(self, argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return subprocess.CompletedProcess(
                args=argv,
                returncode=1,
                stdout="",
                stderr=str(error),
            )
        return result

    def _probe_diagnostic(
        self,
        result: subprocess.CompletedProcess[str],
    ) -> str:
        diagnostic = (result.stderr or result.stdout).strip()
        if not diagnostic:
            return f"exit code {result.returncode}"
        first_line = diagnostic.splitlines()[0].strip()
        return first_line or f"exit code {result.returncode}"

    def _version(self, resolved_path: str) -> str | None:
        try:
            completed = subprocess.run(
                (resolved_path, "--version"),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        version = completed.stdout.strip() or completed.stderr.strip()
        return version or None

    def _common_exec_options(
        self,
        request: ExecutionRequest,
        result_path: Path,
    ) -> tuple[str, ...]:
        options: list[str] = [
            "--json",
            "-C",
            str(Path(request.workspace).resolve()),
            "-o",
            str(result_path),
        ]
        if request.options.model is not None:
            options.extend(("-m", request.options.model))
        if request.options.reasoning_effort is not None:
            options.extend(
                (
                    "-c",
                    f'model_reasoning_effort="{request.options.reasoning_effort}"',
                )
            )
        options.extend(self._execution_policy_options(request))
        sandbox = request.options.sandbox
        if not request.mutation_allowed:
            sandbox = SandboxMode.READ_ONLY
        options.extend(("-s", str(sandbox)))
        if request.options.ephemeral:
            options.append("--ephemeral")
        command_options = tuple(options)
        return command_options

    def _common_resume_options(
        self,
        plan: ExecutionPlan,
        result_path: Path,
    ) -> tuple[str, ...]:
        request = plan.request
        options: list[str] = ["--json", "-o", str(result_path)]
        if request.options.model is not None:
            options.extend(("-m", request.options.model))
        if request.options.reasoning_effort is not None:
            options.extend(
                (
                    "-c",
                    f'model_reasoning_effort="{request.options.reasoning_effort}"',
                )
            )
        options.extend(self._execution_policy_options(request))
        if request.options.ephemeral:
            options.append("--ephemeral")
        command_options = tuple(options)
        return command_options

    def _execution_policy_options(
        self,
        request: ExecutionRequest,
    ) -> tuple[str, ...]:
        options: list[str] = [
            "-c",
            f'approval_policy="{request.options.approval_policy}"',
        ]
        if request.options.search:
            options.extend(("-c", 'web_search="live"'))
        command_options = tuple(options)
        return command_options
