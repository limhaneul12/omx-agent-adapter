from comx_harness.ade.external_tools import ExternalToolService
from comx_harness.ade.tk_refresh import _run_objective_label
from comx_harness.ade.tk_runtime_helpers import (
    launch_observed_tmux,
    provider_readiness_label,
)
from comx_harness.schemas.provider_schemas import (
    CapabilityReport,
    ProviderCapability,
    ProviderInfo,
)
from comx_harness.shared.harness_enums.provider_enums import Operation, ProviderId


def test_provider_label_distinguishes_execution_from_observation() -> None:
    report = CapabilityReport(
        providers=(
            ProviderInfo(
                provider=ProviderId.CODEX,
                binary="codex",
                available=True,
                capabilities=(
                    ProviderCapability(
                        operation=Operation.RUN,
                        supported=True,
                        detail="ready",
                    ),
                ),
            ),
            ProviderInfo(
                provider=ProviderId.OMX,
                binary="omx",
                available=True,
                capabilities=(
                    ProviderCapability(
                        operation=Operation.RUN,
                        supported=False,
                        detail="ambient session conflict",
                    ),
                    ProviderCapability(
                        operation=Operation.STATUS,
                        supported=True,
                        detail="stored Run observation remains available",
                    ),
                ),
            ),
        )
    )

    assert provider_readiness_label(report) == "codex ready · omx observe-only"


class _FakeProcess:
    pid = 2468


def test_tmux_action_launches_only_an_explicit_observed_target() -> None:
    calls: list[tuple[str, ...]] = []

    def launcher(argv: tuple[str, ...], **kwargs: object) -> _FakeProcess:
        del kwargs
        calls.append(argv)
        return _FakeProcess()

    external = ExternalToolService(platform="darwin", launcher=launcher)

    unknown = launch_observed_tmux(external, None)
    observed = launch_observed_tmux(external, "omx-team-alpha")

    assert unknown.launched is False
    assert "explicit observed session identity" in (unknown.message or "")
    assert observed.launched is True
    assert observed.target.argv == (
        "tmux",
        "attach-session",
        "-t",
        "omx-team-alpha",
    )
    assert "explicit observed tmux session identity" in observed.target.evidence
    assert calls == [observed.target.argv]


def test_run_list_objective_is_one_readable_line() -> None:
    label = _run_objective_label(
        "Inspect the implementation.\n"
        "  Do not modify files;   return one concise verdict."
    )

    assert label == (
        "Inspect the implementation. Do not modify files; return one concise verdict."
    )
