from __future__ import annotations

from pathlib import Path

from comx_harness import (
    ExecutionRequest,
    HandoffExecutionRequest,
    HarnessService,
    HarnessTools,
    ResumeRequest,
    RunReference,
)
from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.shared.harness_enums.execution_enums import SandboxMode
from comx_harness.shared.harness_enums.lifecycle_enums import RunStatus
from comx_harness.shared.harness_enums.provider_enums import ProviderId


def test_controller_surface_delegates_all_public_operations(
    tmp_path: Path,
    fake_provider_path: Path,
) -> None:
    service = HarnessService()
    tools = HarnessTools(service)
    execution_request = ExecutionRequest(
        controller_id="hermes-builder",
        provider=ProviderId.CODEX,
        objective="Produce verified controller evidence.",
        workspace=str(tmp_path),
        options=RunOptions(sandbox=SandboxMode.READ_ONLY),
    )

    capabilities = tools.capabilities()
    plan = tools.plan(execution_request)
    source = tools.run(execution_request)
    reference = RunReference(workspace=str(tmp_path), run_id=source.run_id)
    state = tools.status(reference)
    events = tools.events(reference)
    artifacts = tools.artifacts(reference)
    terminal_cancel = tools.cancel(reference)
    resumed = tools.resume(
        ResumeRequest(
            workspace=str(tmp_path),
            run_id=source.run_id,
            objective="Continue through the same typed controller surface.",
        )
    )
    handoff = tools.handoff(
        HandoffExecutionRequest(
            workspace=str(tmp_path),
            controller_id="hermes-reviewer",
            origin_run_id=source.run_id,
            target_provider=ProviderId.OMX,
            objective="Review the verified source artifact.",
            options=RunOptions(sandbox=SandboxMode.READ_ONLY),
        )
    )

    assert tools.service is service
    assert {provider.provider for provider in capabilities.providers} == {
        "codex",
        "omx",
    }
    assert plan.request.controller_id == "hermes-builder"
    assert source.status == RunStatus.SUCCEEDED
    assert state.record.run_id == source.run_id
    assert events.run_id == source.run_id
    assert artifacts.run_id == source.run_id
    assert terminal_cancel.run_id == source.run_id
    assert terminal_cancel.status == RunStatus.SUCCEEDED
    assert resumed.parent_run_id == source.run_id
    assert handoff.handoff.controller_id == "hermes-reviewer"
    assert handoff.handoff.source_provider == "codex"
    assert handoff.handoff.target_provider == "omx"
    assert handoff.target_run.status == RunStatus.SUCCEEDED


def test_controller_surface_exposes_exactly_the_goal_operations() -> None:
    public_methods = {
        name
        for name, value in vars(HarnessTools).items()
        if callable(value) and not name.startswith("_")
    }

    assert public_methods == {
        "artifacts",
        "cancel",
        "capabilities",
        "events",
        "handoff",
        "plan",
        "resume",
        "run",
        "status",
    }


def test_controller_input_contracts_are_strict_json_schemas() -> None:
    schemas = (
        RunReference.model_json_schema(),
        ResumeRequest.model_json_schema(),
        HandoffExecutionRequest.model_json_schema(),
    )

    assert all(schema.get("additionalProperties") is False for schema in schemas)
    assert "workspace" in RunReference.model_fields
    assert "objective" in ResumeRequest.model_fields
    assert "idempotency_key" in ResumeRequest.model_fields
    assert "target_provider" in HandoffExecutionRequest.model_fields
    assert "idempotency_key" in HandoffExecutionRequest.model_fields
