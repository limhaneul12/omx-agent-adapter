from __future__ import annotations

from comx_harness.schemas.artifact_schemas import ArtifactReport
from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.schemas.lifecycle_schemas import EventReport, RunState
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    SandboxMode,
)
from comx_harness.shared.harness_enums.lifecycle_enums import (
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.operator_enums import (
    AttentionEntityKind,
    AttentionKind,
    RecipeId,
    RunDetailTab,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from pydantic import Field


class Recipe(StrictModel):
    recipe_id: RecipeId
    title: NonEmptyString
    description: NonEmptyString
    provider: ProviderId
    mutation_allowed: bool = False
    sandbox: SandboxMode = SandboxMode.READ_ONLY
    approval_policy: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    expected_artifacts: tuple[NonEmptyString, ...] = ()
    search: bool = False
    ephemeral: bool = False
    timeout_seconds: int = Field(default=3600, ge=1, le=86_400)


class AttentionTarget(StrictModel):
    tab: RunDetailTab
    entity_kind: AttentionEntityKind
    entity_id: NonEmptyString


class AttentionItem(StrictModel):
    kind: AttentionKind
    message: NonEmptyString
    evidence: NonEmptyString
    target: AttentionTarget


class RunSummary(StrictModel):
    run_id: NonEmptyString
    provider: ProviderId
    objective: NonEmptyString
    status: RunStatus
    liveness: ProcessLiveness
    started_at: NonEmptyString | None = None
    finished_at: NonEmptyString | None = None
    parent_run_id: NonEmptyString | None = None
    verified_artifact_count: int = Field(ge=0)
    attention: tuple[AttentionItem, ...] = ()


class WorkspaceRunProjection(StrictModel):
    workspace: NonEmptyString
    runs: tuple[RunSummary, ...]


class RunInspection(StrictModel):
    state: RunState
    events: EventReport
    artifacts: ArtifactReport
    discovered_omx_teams: tuple[NonEmptyString, ...] = ()
