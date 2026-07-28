from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from comx_harness.provider_registry import ProviderRegistry
from comx_harness.schemas.execution_schemas import (
    ExecutionPlan,
    ExecutionRequest,
    RunOptions,
)
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    SandboxMode,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.storage.time_identity import utc_timestamp


def _request(workspace: Path, provider: ProviderId) -> ExecutionRequest:
    return ExecutionRequest(
        controller_id="native-parser-test",
        provider=provider,
        objective="Validate the native argument contract.",
        workspace=str(workspace),
        options=RunOptions(
            sandbox=SandboxMode.READ_ONLY,
            approval_policy=ApprovalPolicy.NEVER,
            search=True,
            ephemeral=True,
        ),
    )


def _plan(
    workspace: Path,
    provider: ProviderId,
    request: ExecutionRequest,
    argv: tuple[str, ...],
) -> ExecutionPlan:
    return ExecutionPlan(
        run_id=f"native-parser-{provider}",
        created_at=utc_timestamp(),
        request=request,
        provider=provider,
        argv=argv,
        cwd=str(workspace),
        run_dir=str(workspace / "run"),
        result_path=str(workspace / "result.md"),
        stdout_path=str(workspace / "stdout.log"),
        stderr_path=str(workspace / "stderr.log"),
        events_path=str(workspace / "events.jsonl"),
        supports_cancel=True,
        supports_resume=True,
    )


def _assert_parser_accepts(argv: tuple[str, ...]) -> None:
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    diagnostic = completed.stderr or completed.stdout
    assert completed.returncode == 0, diagnostic
    assert "unexpected argument" not in diagnostic


@pytest.mark.native
@pytest.mark.parametrize("provider", tuple(ProviderId))
def test_installed_native_cli_accepts_run_and_resume_contract(
    tmp_path: Path,
    provider: ProviderId,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if provider == ProviderId.OMX:
        # Parser compatibility is an installed-binary property; an unrelated
        # owning OMX/tmux session must not turn this probe into a launch test.
        for name in tuple(os.environ):
            if name.startswith("OMX") or name in {
                "TMUX",
                "TMUX_PANE",
                "CODEX_THREAD_ID",
            }:
                monkeypatch.delenv(name, raising=False)
        isolated_state_root = tmp_path / "omx-state"
        isolated_state_root.mkdir()
        monkeypatch.setenv("OMX_STATE_ROOT", str(isolated_state_root))
    adapter = ProviderRegistry().get(provider)
    if shutil.which(adapter.binary_name) is None:
        pytest.skip(f"{adapter.binary_name} is not installed")

    request = _request(tmp_path, provider)
    run_argv = adapter.build_run_argv(request, tmp_path / "result.md")
    _assert_parser_accepts((*run_argv[:-1], "--help"))

    plan = _plan(tmp_path, provider, request, run_argv)
    resume_argv = adapter.build_resume_argv(
        plan,
        "00000000-0000-0000-0000-000000000000",
        "Validate resume argument parsing.",
        tmp_path / "resume-result.md",
    )
    _assert_parser_accepts((*resume_argv[:-2], "--help"))
