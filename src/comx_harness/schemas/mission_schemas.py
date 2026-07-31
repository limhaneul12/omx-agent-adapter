from __future__ import annotations

from typing import Annotated, Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.schemas.git_policy_schemas import GitPolicyEvidence
from comx_harness.schemas.strategy_schemas import (
    StrategyArtifactReport,
    StrategyDefinition,
    StrategyEventReport,
    StrategyRecord,
    StrategyValidationReport,
)
from comx_harness.shared.harness_enums.execution_enums import SandboxMode
from comx_harness.shared.harness_enums.mission_enums import MissionExecutionProfile
from pydantic import Field, model_validator

MissionIdentifier = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
]


class MissionConstraints(StrictModel):
    mutation_allowed: bool = False
    preserve_unrelated_changes: bool = True
    commit_allowed: Literal[False] = False
    push_allowed: Literal[False] = False


class MissionVerification(StrictModel):
    require_process_success: bool = True
    require_semantic_success: bool = True
    required_artifacts: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_required_artifacts(self) -> MissionVerification:
        if len(self.required_artifacts) != len(set(self.required_artifacts)):
            raise ValueError("required_artifacts must be unique")
        validated = self
        return validated


class MissionRequest(StrictModel):
    schema_version: Literal["mission-request.v1"] = "mission-request.v1"
    mission_id: MissionIdentifier
    controller_id: NonEmptyString = "human-cli"
    objective: NonEmptyString
    workspace: NonEmptyString = "."
    execution_profile: MissionExecutionProfile
    constraints: MissionConstraints = MissionConstraints()
    verification: MissionVerification = MissionVerification()
    timeout_seconds: int = Field(default=3600, ge=1, le=86_400)
    options: RunOptions = RunOptions()

    @model_validator(mode="after")
    def validate_safety_boundary(self) -> MissionRequest:
        if (
            not self.constraints.mutation_allowed
            and self.options.sandbox != SandboxMode.READ_ONLY
        ):
            raise ValueError("mutation_allowed=false requires sandbox=read-only")
        if (
            self.constraints.mutation_allowed
            and self.options.sandbox == SandboxMode.READ_ONLY
        ):
            raise ValueError(
                "mutation_allowed=true requires an explicit writable sandbox"
            )
        if (
            self.execution_profile == MissionExecutionProfile.CODEX_THEN_OMX_REVIEW
            and not self.constraints.mutation_allowed
        ):
            raise ValueError(
                "codex-then-omx-review requires mutation_allowed=true because the "
                "reviewer must emit a verified blocker artifact"
            )
        validated = self
        return validated


class MissionPlan(StrictModel):
    schema_version: Literal["mission-plan.v1"] = "mission-plan.v1"
    request: MissionRequest
    strategy: StrategyDefinition
    decisions: tuple[NonEmptyString, ...]


class MissionValidationReport(StrictModel):
    schema_version: Literal["mission-validation.v1"] = "mission-validation.v1"
    mission_id: MissionIdentifier
    valid: bool
    plan: MissionPlan
    strategy_validation: StrategyValidationReport


class MissionRecord(StrictModel):
    schema_version: Literal["mission-record.v1"] = "mission-record.v1"
    mission_id: MissionIdentifier
    request: MissionRequest
    strategy_id: NonEmptyString
    created_at: NonEmptyString
    updated_at: NonEmptyString


class MissionStatusReport(StrictModel):
    schema_version: Literal["mission-status.v1"] = "mission-status.v1"
    mission: MissionRecord
    strategy: StrategyRecord
    git_policy_evidence: GitPolicyEvidence | None = None


class MissionEventReport(StrictModel):
    schema_version: Literal["mission-events.v1"] = "mission-events.v1"
    mission_id: MissionIdentifier
    strategy_events: StrategyEventReport


class MissionArtifactReport(StrictModel):
    schema_version: Literal["mission-artifacts.v1"] = "mission-artifacts.v1"
    mission_id: MissionIdentifier
    strategy_artifacts: StrategyArtifactReport
