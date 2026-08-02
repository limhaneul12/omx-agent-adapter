from __future__ import annotations

from typing import Annotated, Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.shared.harness_enums.execution_enums import (
    SandboxMode,
)
from pydantic import Field, StrictInt, field_validator, model_validator

_RESERVED_CODEX_AGENT_NAMES = frozenset(
    {
        "default_subagent_model",
        "default_subagent_reasoning_effort",
        "enabled",
        "interrupt_message",
        "max_concurrent_threads_per_session",
        "max_threads",
    }
)

CodexSubagentName = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$"),
]
CodexModelId = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
]


CodexSubagentReasoningEffort = Literal["low", "medium", "high", "xhigh", "max"]


class CodexSubagentSpec(StrictModel):
    name: CodexSubagentName
    description: NonEmptyString
    developer_instructions: NonEmptyString
    model: CodexModelId
    model_reasoning_effort: CodexSubagentReasoningEffort
    sandbox_mode: SandboxMode

    @field_validator("name")
    @classmethod
    def _reject_reserved_name(cls, value: str) -> str:
        if value in _RESERVED_CODEX_AGENT_NAMES:
            raise ValueError(f"{value!r} is reserved by Codex agent settings")
        return value

    @field_validator("description", "developer_instructions")
    @classmethod
    def _reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain a non-whitespace character")
        return value

    @field_validator("sandbox_mode")
    @classmethod
    def _restrict_sandbox(cls, value: SandboxMode) -> SandboxMode:
        if value == SandboxMode.DANGER_FULL_ACCESS:
            raise ValueError(
                "Codex subagents support only read-only or workspace-write sandbox_mode"
            )
        return value


class CodexSubagentRegistrationSpec(StrictModel):
    schema_version: Literal["codex-subagent-registration.v1"]
    max_concurrent_threads_per_session: StrictInt | None = Field(
        default=None,
        ge=1,
        le=64,
    )
    agents: tuple[CodexSubagentSpec, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _reject_duplicate_names(self) -> CodexSubagentRegistrationSpec:
        names = tuple(agent.name for agent in self.agents)
        if len(names) != len(set(names)):
            raise ValueError("agent names must be unique")
        return self


class CodexSubagentFileConfig(StrictModel):
    model: CodexModelId
    model_reasoning_effort: CodexSubagentReasoningEffort
    sandbox_mode: SandboxMode
    developer_instructions: NonEmptyString

    @field_validator("developer_instructions")
    @classmethod
    def _reject_blank_instructions(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("developer_instructions must not be blank")
        return value

    @field_validator("sandbox_mode")
    @classmethod
    def _restrict_sandbox(cls, value: SandboxMode) -> SandboxMode:
        if value == SandboxMode.DANGER_FULL_ACCESS:
            raise ValueError(
                "Codex subagents support only read-only or workspace-write sandbox_mode"
            )
        return value


class CodexSubagentPlannedFile(StrictModel):
    name: CodexSubagentName
    config_file: NonEmptyString
    destination: NonEmptyString


class CodexSubagentValidationReport(StrictModel):
    schema_version: Literal["codex-subagent-validation-report.v1"] = (
        "codex-subagent-validation-report.v1"
    )
    valid: Literal[True] = True
    workspace: NonEmptyString
    config_path: NonEmptyString
    max_concurrent_threads_per_session: int | None
    agents: tuple[CodexSubagentPlannedFile, ...]
    warnings: tuple[NonEmptyString, ...]
    mutation_performed: Literal[False] = False


class CodexRegisteredSubagentState(StrictModel):
    name: str
    description: NonEmptyString | None
    config_file: NonEmptyString | None
    file_exists: bool
    valid: bool
    model: NonEmptyString | None
    model_reasoning_effort: NonEmptyString | None
    sandbox_mode: NonEmptyString | None
    developer_instructions: NonEmptyString | None
    warnings: tuple[NonEmptyString, ...]


class CodexSubagentRegistryState(StrictModel):
    schema_version: Literal["codex-subagent-registry-state.v1"] = (
        "codex-subagent-registry-state.v1"
    )
    workspace: NonEmptyString
    config_path: NonEmptyString
    config_exists: bool
    max_concurrent_threads_per_session: int | None
    agents: tuple[CodexRegisteredSubagentState, ...]
    warnings: tuple[NonEmptyString, ...]
    valid: bool


class CodexSubagentRegistrationReport(StrictModel):
    schema_version: Literal["codex-subagent-registration-report.v1"] = (
        "codex-subagent-registration-report.v1"
    )
    workspace: NonEmptyString
    config_path: NonEmptyString
    written_files: tuple[NonEmptyString, ...]
    registry: CodexSubagentRegistryState
