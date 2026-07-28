from __future__ import annotations

from typing import Literal

from comx_harness.schemas.common_schemas import (
    NonEmptyString,
    Sha256Digest,
    StrictModel,
)
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    ReasoningEffort,
    SandboxMode,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from pydantic import Field, model_validator


class RunOptions(StrictModel):
    model: NonEmptyString | None = None
    reasoning_effort: ReasoningEffort | None = None
    sandbox: SandboxMode = SandboxMode.READ_ONLY
    approval_policy: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    search: bool = False
    ephemeral: bool = False


class ExecutionRequest(StrictModel):
    controller_id: NonEmptyString = "human-cli"
    provider: ProviderId
    objective: NonEmptyString
    workspace: NonEmptyString = "."
    mutation_allowed: bool = False
    timeout_seconds: int = Field(default=3600, ge=1, le=86_400)
    idempotency_key: NonEmptyString | None = None
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    options: RunOptions = RunOptions()

    @model_validator(mode="after")
    def validate_mutation_boundary(self) -> ExecutionRequest:
        if not self.mutation_allowed and self.options.sandbox != SandboxMode.READ_ONLY:
            raise ValueError("mutation_allowed=false requires sandbox=read-only")
        if len(self.expected_artifacts) != len(set(self.expected_artifacts)):
            raise ValueError("expected_artifacts must be unique")
        validated_request = self
        return validated_request


class IdempotencyBinding(StrictModel):
    schema_version: Literal["idempotency-binding.v1"] = "idempotency-binding.v1"
    key_sha256: Sha256Digest
    request_sha256: Sha256Digest
    run_id: NonEmptyString


class ExecutionPlan(StrictModel):
    schema_version: Literal["execution-plan.v1"] = "execution-plan.v1"
    run_id: NonEmptyString
    created_at: NonEmptyString
    request: ExecutionRequest
    provider: ProviderId
    argv: tuple[NonEmptyString, ...]
    cwd: NonEmptyString
    run_dir: NonEmptyString
    result_path: NonEmptyString
    stdout_path: NonEmptyString
    stderr_path: NonEmptyString
    events_path: NonEmptyString
    supports_cancel: bool
    supports_resume: bool
    parent_run_id: NonEmptyString | None = None
    resume_session_id: NonEmptyString | None = None


class RunReference(StrictModel):
    workspace: NonEmptyString = "."
    run_id: NonEmptyString


class ResumeRequest(RunReference):
    objective: NonEmptyString | None = None
    idempotency_key: NonEmptyString | None = None
