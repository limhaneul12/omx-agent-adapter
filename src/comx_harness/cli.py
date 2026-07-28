from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from comx_harness.ade.agent_cli import agent_app
from comx_harness.ade.desktop_launcher import launch_desktop_ade
from comx_harness.cli_output import emit_model, fail_operation
from comx_harness.controller_surface import HarnessTools
from comx_harness.schemas.execution_schemas import (
    ExecutionRequest,
    ResumeRequest,
    RunOptions,
    RunReference,
)
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest
from comx_harness.shared.exceptions.harness_exceptions import HarnessError
from comx_harness.shared.exceptions.provider_exceptions import ProviderUnavailableError
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    ReasoningEffort,
    SandboxMode,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId

app = typer.Typer(
    help=(
        "Local Agent Development Environment backed by one controller-neutral "
        "Codex/OMX execution core."
    ),
    add_completion=False,
    no_args_is_help=True,
)
app.add_typer(agent_app, name="agent")


def _tools() -> HarnessTools:
    return HarnessTools()


def _run_options(
    *,
    model: str | None,
    reasoning_effort: str | None,
    sandbox: str,
    approval_policy: str,
    search: bool,
    ephemeral: bool,
) -> RunOptions:
    options = RunOptions(
        model=model,
        reasoning_effort=(
            ReasoningEffort(reasoning_effort) if reasoning_effort is not None else None
        ),
        sandbox=SandboxMode(sandbox),
        approval_policy=ApprovalPolicy(approval_policy),
        search=search,
        ephemeral=ephemeral,
    )
    return options


def _execution_request(
    *,
    provider: str,
    objective: str,
    controller_id: str,
    cwd: Path,
    mutation_allowed: bool,
    timeout_seconds: int,
    idempotency_key: str | None,
    expected_artifacts: list[str],
    model: str | None,
    reasoning_effort: str | None,
    sandbox: str,
    approval_policy: str,
    search: bool,
    ephemeral: bool,
) -> ExecutionRequest:
    request = ExecutionRequest(
        controller_id=controller_id,
        provider=ProviderId(provider),
        objective=objective,
        workspace=str(cwd),
        mutation_allowed=mutation_allowed,
        timeout_seconds=timeout_seconds,
        idempotency_key=idempotency_key,
        expected_artifacts=tuple(expected_artifacts),
        options=_run_options(
            model=model,
            reasoning_effort=reasoning_effort,
            sandbox=sandbox,
            approval_policy=approval_policy,
            search=search,
            ephemeral=ephemeral,
        ),
    )
    return request


@app.command("ade")
def ade_command(
    cwd: Path = typer.Option(Path("."), "--cwd"),
) -> None:
    """Open the local Codex/OMX Agent Development Environment."""
    launch_desktop_ade(cwd)


@app.command("capabilities")
def capabilities_command() -> None:
    """Discover installed providers and their supported harness operations."""
    try:
        emit_model(_tools().capabilities())
    except (HarnessError, ProviderUnavailableError, ValidationError, OSError) as error:
        fail_operation(error)


@app.command("plan")
def plan_command(
    objective: str = typer.Argument(..., help="Goal for the native runtime."),
    provider: str = typer.Option("codex", "--provider", help="codex or omx"),
    controller_id: str = typer.Option("human-cli", "--controller"),
    cwd: Path = typer.Option(Path("."), "--cwd"),
    mutation_allowed: bool = typer.Option(False, "--mutation/--read-only"),
    timeout_seconds: int = typer.Option(3600, "--timeout"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key"),
    expected_artifacts: list[str] = typer.Option([], "--expected-artifact"),
    model: str | None = typer.Option(None, "--model"),
    reasoning_effort: str | None = typer.Option(None, "--reasoning-effort"),
    sandbox: str = typer.Option("read-only", "--sandbox"),
    approval_policy: str = typer.Option("on-request", "--approval"),
    search: bool = typer.Option(False, "--search"),
    ephemeral: bool = typer.Option(False, "--ephemeral"),
) -> None:
    """Preview the exact typed execution contract without launching it."""
    try:
        request = _execution_request(
            provider=provider,
            objective=objective,
            controller_id=controller_id,
            cwd=cwd,
            mutation_allowed=mutation_allowed,
            timeout_seconds=timeout_seconds,
            idempotency_key=idempotency_key,
            expected_artifacts=expected_artifacts,
            model=model,
            reasoning_effort=reasoning_effort,
            sandbox=sandbox,
            approval_policy=approval_policy,
            search=search,
            ephemeral=ephemeral,
        )
        emit_model(_tools().plan(request))
    except (
        HarnessError,
        ProviderUnavailableError,
        ValidationError,
        ValueError,
        OSError,
    ) as error:
        fail_operation(error)


@app.command("run")
def run_command(
    objective: str = typer.Argument(..., help="Goal for the native runtime."),
    provider: str = typer.Option("codex", "--provider", help="codex or omx"),
    controller_id: str = typer.Option("human-cli", "--controller"),
    cwd: Path = typer.Option(Path("."), "--cwd"),
    mutation_allowed: bool = typer.Option(False, "--mutation/--read-only"),
    timeout_seconds: int = typer.Option(3600, "--timeout"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key"),
    expected_artifacts: list[str] = typer.Option([], "--expected-artifact"),
    model: str | None = typer.Option(None, "--model"),
    reasoning_effort: str | None = typer.Option(None, "--reasoning-effort"),
    sandbox: str = typer.Option("read-only", "--sandbox"),
    approval_policy: str = typer.Option("on-request", "--approval"),
    search: bool = typer.Option(False, "--search"),
    ephemeral: bool = typer.Option(False, "--ephemeral"),
) -> None:
    """Execute one task on one native provider and verify its evidence."""
    try:
        request = _execution_request(
            provider=provider,
            objective=objective,
            controller_id=controller_id,
            cwd=cwd,
            mutation_allowed=mutation_allowed,
            timeout_seconds=timeout_seconds,
            idempotency_key=idempotency_key,
            expected_artifacts=expected_artifacts,
            model=model,
            reasoning_effort=reasoning_effort,
            sandbox=sandbox,
            approval_policy=approval_policy,
            search=search,
            ephemeral=ephemeral,
        )
        emit_model(_tools().run(request))
    except (
        HarnessError,
        ProviderUnavailableError,
        ValidationError,
        ValueError,
        OSError,
    ) as error:
        fail_operation(error)


@app.command("handoff")
def handoff_command(
    origin_run_id: str = typer.Argument(...),
    objective: str = typer.Argument(..., help="Goal for the receiving runtime."),
    target_provider: str = typer.Option(..., "--target-provider"),
    artifact_kind: str = typer.Option("result", "--artifact"),
    controller_id: str = typer.Option("human-cli", "--controller"),
    cwd: Path = typer.Option(Path("."), "--cwd"),
    mutation_allowed: bool = typer.Option(False, "--mutation/--read-only"),
    timeout_seconds: int = typer.Option(3600, "--timeout"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key"),
    model: str | None = typer.Option(None, "--model"),
    reasoning_effort: str | None = typer.Option(None, "--reasoning-effort"),
    sandbox: str = typer.Option("read-only", "--sandbox"),
    approval_policy: str = typer.Option("on-request", "--approval"),
    search: bool = typer.Option(False, "--search"),
    ephemeral: bool = typer.Option(False, "--ephemeral"),
) -> None:
    """Pass one verified artifact into a different native provider."""
    try:
        request = HandoffExecutionRequest(
            workspace=str(cwd),
            controller_id=controller_id,
            origin_run_id=origin_run_id,
            target_provider=ProviderId(target_provider),
            objective=objective,
            artifact_kind=artifact_kind,
            timeout_seconds=timeout_seconds,
            mutation_allowed=mutation_allowed,
            idempotency_key=idempotency_key,
            options=_run_options(
                model=model,
                reasoning_effort=reasoning_effort,
                sandbox=sandbox,
                approval_policy=approval_policy,
                search=search,
                ephemeral=ephemeral,
            ),
        )
        emit_model(_tools().handoff(request))
    except (
        HarnessError,
        ProviderUnavailableError,
        ValidationError,
        ValueError,
        OSError,
    ) as error:
        fail_operation(error)


@app.command("status")
def status_command(
    run_id: str = typer.Argument(...),
    cwd: Path = typer.Option(Path("."), "--cwd"),
) -> None:
    """Read normalized semantic state and process liveness."""
    try:
        emit_model(_tools().status(RunReference(workspace=str(cwd), run_id=run_id)))
    except (HarnessError, ValidationError, OSError) as error:
        fail_operation(error)


@app.command("events")
def events_command(
    run_id: str = typer.Argument(...),
    cwd: Path = typer.Option(Path("."), "--cwd"),
) -> None:
    """Read normalized lifecycle and native provider events."""
    try:
        emit_model(_tools().events(RunReference(workspace=str(cwd), run_id=run_id)))
    except (HarnessError, ValidationError, OSError) as error:
        fail_operation(error)


@app.command("cancel")
def cancel_command(
    run_id: str = typer.Argument(...),
    cwd: Path = typer.Option(Path("."), "--cwd"),
) -> None:
    """Request bounded cancellation of a recorded native process."""
    try:
        emit_model(_tools().cancel(RunReference(workspace=str(cwd), run_id=run_id)))
    except (HarnessError, ValidationError, OSError) as error:
        fail_operation(error)


@app.command("resume")
def resume_command(
    run_id: str = typer.Argument(...),
    objective: str | None = typer.Option(None, "--objective"),
    cwd: Path = typer.Option(Path("."), "--cwd"),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key"),
) -> None:
    """Resume a run only when a native provider session id is available."""
    try:
        emit_model(
            _tools().resume(
                ResumeRequest(
                    workspace=str(cwd),
                    run_id=run_id,
                    objective=objective,
                    idempotency_key=idempotency_key,
                )
            )
        )
    except (
        HarnessError,
        ProviderUnavailableError,
        ValidationError,
        OSError,
    ) as error:
        fail_operation(error)


@app.command("artifacts")
def artifacts_command(
    run_id: str = typer.Argument(...),
    cwd: Path = typer.Option(Path("."), "--cwd"),
) -> None:
    """Read verified result, log, event, plan, and declared artifacts."""
    try:
        emit_model(_tools().artifacts(RunReference(workspace=str(cwd), run_id=run_id)))
    except (HarnessError, ValidationError, OSError) as error:
        fail_operation(error)


if __name__ == "__main__":
    app()
