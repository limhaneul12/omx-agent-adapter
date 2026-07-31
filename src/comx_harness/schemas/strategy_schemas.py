from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from comx_harness.shared.harness_enums.strategy_enums import (
    NativeCapability,
    StrategyEventKind,
    StrategyFailureAction,
    StrategyNodeType,
    StrategyRunCondition,
    StrategyStageStatus,
    StrategyStatus,
    StrategyValidatorKind,
)
from pydantic import Field, model_validator

StrategyIdentifier = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
]


class StrategyCompletionCriteria(StrictModel):
    require_process_success: bool = True
    require_semantic_success: bool = True
    required_artifacts: tuple[NonEmptyString, ...] = ()
    max_blockers: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_required_artifacts(self) -> StrategyCompletionCriteria:
        if len(self.required_artifacts) != len(set(self.required_artifacts)):
            raise ValueError("required_artifacts must be unique")
        return self


class StrategyFailurePolicy(StrictModel):
    action: StrategyFailureAction = StrategyFailureAction.STOP
    max_attempts: int = Field(default=1, ge=1, le=3)


class StrategyStage(StrictModel):
    stage_id: NonEmptyString
    node_type: StrategyNodeType
    provider: ProviderId | None = None
    native_surface: NonEmptyString | None = None
    workflow: NonEmptyString | None = None
    objective: NonEmptyString
    workspace: NonEmptyString
    dependencies: tuple[NonEmptyString, ...] = ()
    input_artifacts: tuple[NonEmptyString, ...] = ()
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    completion_criteria: StrategyCompletionCriteria = StrategyCompletionCriteria()
    failure_policy: StrategyFailurePolicy = StrategyFailurePolicy()
    run_condition: StrategyRunCondition = (
        StrategyRunCondition.ALL_DEPENDENCIES_SUCCEEDED
    )
    capability_requirements: tuple[NativeCapability, ...] = ()
    source_stage_id: NonEmptyString | None = None
    validator_kind: StrategyValidatorKind | None = None
    mutation_allowed: bool = False
    timeout_seconds: int = Field(default=3600, ge=1, le=86_400)
    options: RunOptions = RunOptions()

    @model_validator(mode="after")
    def validate_node_contract(self) -> StrategyStage:
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("dependencies must be unique")
        if len(self.input_artifacts) != len(set(self.input_artifacts)):
            raise ValueError("input_artifacts must be unique")
        if len(self.expected_artifacts) != len(set(self.expected_artifacts)):
            raise ValueError("expected_artifacts must be unique")
        if len(self.capability_requirements) != len(set(self.capability_requirements)):
            raise ValueError("capability_requirements must be unique")
        if (
            self.run_condition != StrategyRunCondition.ALL_DEPENDENCIES_SUCCEEDED
            and not self.dependencies
        ):
            raise ValueError("conditional stages require dependencies")

        provider_nodes = {
            StrategyNodeType.NATIVE_RUN,
            StrategyNodeType.NATIVE_RESUME,
            StrategyNodeType.HANDOFF,
        }
        if self.node_type in provider_nodes and self.provider is None:
            raise ValueError(f"{self.node_type} requires provider")
        if self.node_type not in provider_nodes and self.provider is not None:
            raise ValueError(f"{self.node_type} must not set provider")

        if self.node_type == StrategyNodeType.NATIVE_RUN:
            if self.native_surface is None and self.workflow is None:
                raise ValueError("native_run requires native_surface or workflow")
            if self.source_stage_id is not None or self.validator_kind is not None:
                raise ValueError(
                    "native_run cannot set source_stage_id or validator_kind"
                )
        elif self.node_type in {
            StrategyNodeType.NATIVE_RESUME,
            StrategyNodeType.HANDOFF,
        }:
            if self.source_stage_id is None:
                raise ValueError(f"{self.node_type} requires source_stage_id")
            if self.validator_kind is not None:
                raise ValueError(f"{self.node_type} cannot set validator_kind")
        elif self.node_type == StrategyNodeType.VALIDATOR:
            if self.validator_kind is None:
                raise ValueError("validator requires validator_kind")
            if self.source_stage_id is None:
                raise ValueError("validator requires source_stage_id")
            if self.native_surface is not None or self.workflow is not None:
                raise ValueError("validator cannot set native_surface or workflow")
            if (
                self.validator_kind == StrategyValidatorKind.BLOCKER_COUNT
                and len(self.input_artifacts) != 1
            ):
                raise ValueError("blocker_count validator requires one input artifact")
        elif self.node_type == StrategyNodeType.FINISH:
            if self.source_stage_id is not None or self.validator_kind is not None:
                raise ValueError("finish cannot set source_stage_id or validator_kind")
            if self.native_surface is not None or self.workflow is not None:
                raise ValueError("finish cannot set native_surface or workflow")
        return self


class StrategyDefinition(StrictModel):
    schema_version: Literal["strategy-definition.v1"] = "strategy-definition.v1"
    strategy_id: StrategyIdentifier
    controller_id: NonEmptyString = "trusted-agent"
    mission: NonEmptyString
    stages: tuple[StrategyStage, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_sequence(self) -> StrategyDefinition:
        stage_ids = tuple(stage.stage_id for stage in self.stages)
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("stage_id values must be unique")
        known_ids: set[str] = set()
        workspace = Path(self.stages[0].workspace).expanduser().resolve()
        for stage in self.stages:
            if Path(stage.workspace).expanduser().resolve() != workspace:
                raise ValueError(
                    "strategy-definition.v1 supports one shared workspace only"
                )
            missing = tuple(
                dependency
                for dependency in stage.dependencies
                if dependency not in known_ids
            )
            if missing:
                raise ValueError(
                    f"stage {stage.stage_id} has non-previous dependencies: {missing}"
                )
            if (
                stage.source_stage_id is not None
                and stage.source_stage_id not in stage.dependencies
            ):
                raise ValueError(
                    f"stage {stage.stage_id} source_stage_id must be a dependency"
                )
            known_ids.add(stage.stage_id)
        if self.stages[-1].node_type != StrategyNodeType.FINISH:
            raise ValueError("the final stage must be finish")
        if any(
            stage.node_type == StrategyNodeType.FINISH for stage in self.stages[:-1]
        ):
            raise ValueError("finish is allowed only as the final stage")
        return self


class StrategyValidationIssue(StrictModel):
    stage_id: NonEmptyString | None = None
    code: NonEmptyString
    detail: NonEmptyString


class BlockerReport(StrictModel):
    schema_version: Literal["blocker-report.v1"] = "blocker-report.v1"
    blocker_count: int = Field(ge=0, le=10_000)
    unresolved: tuple[NonEmptyString, ...] = ()


class StrategyValidationReport(StrictModel):
    schema_version: Literal["strategy-validation.v1"] = "strategy-validation.v1"
    strategy_id: NonEmptyString
    valid: bool
    issues: tuple[StrategyValidationIssue, ...] = ()


class StrategyEvidence(StrictModel):
    kind: NonEmptyString
    passed: bool
    detail: NonEmptyString
    digest: NonEmptyString | None = None


class StrategyStageRecord(StrictModel):
    stage_id: NonEmptyString
    node_type: StrategyNodeType
    status: StrategyStageStatus
    provider: ProviderId | None = None
    run_id: NonEmptyString | None = None
    handoff_id: NonEmptyString | None = None
    attempts: int = Field(default=0, ge=0, le=3)
    started_at: NonEmptyString | None = None
    completed_at: NonEmptyString | None = None
    evidence: tuple[StrategyEvidence, ...] = ()
    failure: NonEmptyString | None = None


class StrategyRecord(StrictModel):
    schema_version: Literal["strategy-record.v1"] = "strategy-record.v1"
    definition: StrategyDefinition
    status: StrategyStatus
    created_at: NonEmptyString
    updated_at: NonEmptyString
    current_stage_id: NonEmptyString | None = None
    stages: tuple[StrategyStageRecord, ...]


class StrategyEvent(StrictModel):
    schema_version: Literal["strategy-event.v1"] = "strategy-event.v1"
    strategy_id: NonEmptyString
    sequence: int = Field(ge=1)
    timestamp: NonEmptyString
    kind: StrategyEventKind
    message: NonEmptyString
    stage_id: NonEmptyString | None = None
    detail_json: NonEmptyString | None = None


class StrategyEventReport(StrictModel):
    strategy_id: NonEmptyString
    events: tuple[StrategyEvent, ...]


class StrategyArtifact(StrictModel):
    stage_id: NonEmptyString
    run_id: NonEmptyString
    artifact: VerifiedArtifact


class StrategyArtifactReport(StrictModel):
    strategy_id: NonEmptyString
    artifacts: tuple[StrategyArtifact, ...]


class StrategyLaunchRecord(StrictModel):
    schema_version: Literal["strategy-launch.v1"] = "strategy-launch.v1"
    strategy_id: StrategyIdentifier
    workspace: NonEmptyString
    status: Literal["queued", "running", "succeeded", "failed"]
    created_at: NonEmptyString
    request_path: NonEmptyString
    result_path: NonEmptyString
    stdout_path: NonEmptyString
    stderr_path: NonEmptyString
    pid: int | None = Field(default=None, ge=1)
    started_at: NonEmptyString | None = None
    finished_at: NonEmptyString | None = None
    error_message: NonEmptyString | None = None
