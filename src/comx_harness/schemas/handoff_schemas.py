from typing import Literal

from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from pydantic import Field


class HandoffRequest(StrictModel):
    controller_id: NonEmptyString = "human-cli"
    origin_run_id: NonEmptyString
    target_provider: ProviderId
    objective: NonEmptyString
    artifact_kind: NonEmptyString = "result"
    timeout_seconds: int = Field(default=3600, ge=1, le=86_400)
    mutation_allowed: bool = False
    idempotency_key: NonEmptyString | None = None
    options: RunOptions = RunOptions()


class HandoffExecutionRequest(HandoffRequest):
    workspace: NonEmptyString = "."


class HandoffRecord(StrictModel):
    schema_version: Literal["handoff-record.v1"] = "handoff-record.v1"
    handoff_id: NonEmptyString
    created_at: NonEmptyString
    controller_id: NonEmptyString
    origin_run_id: NonEmptyString
    source_provider: ProviderId
    target_provider: ProviderId
    source_artifact: VerifiedArtifact
    target_run_id: NonEmptyString


class HandoffResult(StrictModel):
    handoff: HandoffRecord
    target_run: RunRecord
