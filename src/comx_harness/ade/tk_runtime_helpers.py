from __future__ import annotations

from comx_harness.ade.external_tools import ExternalToolService
from comx_harness.schemas.ade_inspection_schemas import ExternalToolLaunch
from comx_harness.schemas.provider_schemas import CapabilityReport
from comx_harness.shared.harness_enums.provider_enums import Operation


def provider_readiness_label(report: CapabilityReport) -> str:
    labels: list[str] = []
    for provider in report.providers:
        run_capability = next(
            (
                capability
                for capability in provider.capabilities
                if capability.operation == Operation.RUN
            ),
            None,
        )
        state = (
            "missing"
            if not provider.available
            else "ready"
            if run_capability is not None and run_capability.supported
            else "observe-only"
        )
        labels.append(f"{provider.provider} {state}")
    return " · ".join(labels) or "none available"


def launch_observed_tmux(
    external: ExternalToolService,
    session_id: str | None,
) -> ExternalToolLaunch:
    """Launch only a tmux identity backed by observed native evidence."""
    target = external.tmux_attach_target(session_id)
    if not target.supported:
        return ExternalToolLaunch(target=target, message=target.message)
    return external.launch(target)
