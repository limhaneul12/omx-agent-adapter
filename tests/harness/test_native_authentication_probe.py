from __future__ import annotations

import subprocess

import comx_harness.native_provider.omx_provider as omx_provider_module
import comx_harness.native_provider.provider_adapter as provider_adapter_module
import pytest
from comx_harness.native_provider.codex_provider import CodexProvider
from comx_harness.native_provider.omx_provider import OmxProvider
from comx_harness.shared.harness_enums.strategy_enums import CapabilitySupport


def _completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=("codex", "login", "status"),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_codex_authentication_probe_reports_local_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: _completed(0, stdout="Logged in using ChatGPT\n"),
    )

    probe = CodexProvider()._probe_authentication("/fake/codex")

    assert probe.support == CapabilitySupport.SUPPORTED
    assert "active local ChatGPT login" in probe.detail


def test_codex_authentication_probe_reports_logged_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        provider_adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: _completed(1, stderr="Not logged in"),
    )

    probe = CodexProvider()._probe_authentication("/fake/codex")

    assert probe.support == CapabilitySupport.UNSUPPORTED
    assert probe.detail == "Not logged in"


def test_omx_authentication_is_conditional_on_local_codex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        omx_provider_module.shutil,
        "which",
        lambda binary: "/fake/codex" if binary == "codex" else None,
    )
    monkeypatch.setattr(
        provider_adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: _completed(0, stdout="Logged in using ChatGPT\n"),
    )

    probe = OmxProvider()._probe_authentication("/fake/omx")

    assert probe.support == CapabilitySupport.CONDITIONAL
    assert "locally authenticated Codex" in probe.detail
