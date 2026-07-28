from __future__ import annotations

from typing import Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.schemas.execution_schemas import (
    ExecutionRequest,
    ResumeRequest,
)
from comx_harness.schemas.handoff_schemas import HandoffExecutionRequest
from pydantic import model_validator

ArtifactContentState = Literal[
    "available",
    "missing",
    "binary",
    "too_large",
    "error",
]


class GitChangedFile(StrictModel):
    path: NonEmptyString
    original_path: NonEmptyString | None = None
    staged_status: NonEmptyString | None = None
    unstaged_status: NonEmptyString | None = None
    untracked: bool = False


class GitDiffProjection(StrictModel):
    schema_version: Literal["ade-git-diff.v1"] = "ade-git-diff.v1"
    workspace: NonEmptyString
    state: Literal["available", "unknown", "error"]
    files: tuple[GitChangedFile, ...] = ()
    staged_diff: str = ""
    unstaged_diff: str = ""
    message: str | None = None


class ArtifactContentProjection(StrictModel):
    """Bounded, verified artifact content prepared for human inspection."""

    schema_version: Literal["ade-artifact-content.v1"] = "ade-artifact-content.v1"
    run_id: NonEmptyString
    kind: NonEmptyString
    path: NonEmptyString
    state: ArtifactContentState
    size_bytes: int
    text: str | None
    message: str | None


class ExternalToolTarget(StrictModel):
    schema_version: Literal["ade-external-target.v1"] = "ade-external-target.v1"
    kind: Literal["finder", "editor", "terminal", "tmux"]
    supported: bool
    argv: tuple[NonEmptyString, ...] = ()
    evidence: NonEmptyString
    message: str | None = None


class ExternalToolLaunch(StrictModel):
    target: ExternalToolTarget
    pid: int | None = None
    launched: bool = False
    message: str | None = None


class DetachedOperationRequest(StrictModel):
    schema_version: Literal["ade-detached-request.v1"] = "ade-detached-request.v1"
    operation: Literal["run", "resume", "handoff"]
    request: ExecutionRequest | ResumeRequest | HandoffExecutionRequest

    @model_validator(mode="after")
    def validate_request_type(self) -> DetachedOperationRequest:
        expected_type = {
            "run": ExecutionRequest,
            "resume": ResumeRequest,
            "handoff": HandoffExecutionRequest,
        }[self.operation]
        if not isinstance(self.request, expected_type):
            raise ValueError(f"{self.operation} has the wrong request contract")
        return self


class DetachedOperationRecord(StrictModel):
    schema_version: Literal["ade-detached-operation.v1"] = "ade-detached-operation.v1"
    operation_id: NonEmptyString
    operation: Literal["run", "resume", "handoff"]
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: NonEmptyString
    started_at: NonEmptyString | None = None
    finished_at: NonEmptyString | None = None
    pid: int | None = None
    request_path: NonEmptyString
    result_path: NonEmptyString
    stdout_path: NonEmptyString
    stderr_path: NonEmptyString
    error_message: str | None = None
