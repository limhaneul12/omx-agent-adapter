from typing import Literal

from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.shared.harness_enums.lifecycle_enums import (
    EventKind,
    ProcessLiveness,
    RunStatus,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from pydantic import Field


class RunFailure(StrictModel):
    code: NonEmptyString
    message: NonEmptyString
    retryable: bool = False


class RunRecord(StrictModel):
    schema_version: Literal["run-record.v1"] = "run-record.v1"
    run_id: NonEmptyString
    owner_controller_id: NonEmptyString
    provider: ProviderId
    objective: NonEmptyString
    status: RunStatus
    plan_path: NonEmptyString
    pid: int | None = Field(default=None, ge=1)
    started_at: NonEmptyString | None = None
    finished_at: NonEmptyString | None = None
    exit_code: int | None = None
    provider_session_id: NonEmptyString | None = None
    verified_artifacts: tuple[VerifiedArtifact, ...] = ()
    failure: RunFailure | None = None
    parent_run_id: NonEmptyString | None = None


class RunState(StrictModel):
    record: RunRecord
    liveness: ProcessLiveness


class RunEvent(StrictModel):
    schema_version: Literal["run-event.v1"] = "run-event.v1"
    run_id: NonEmptyString
    sequence: int = Field(ge=1)
    timestamp: NonEmptyString
    kind: EventKind
    message: NonEmptyString
    provider_event_type: NonEmptyString | None = None
    provider_payload_json: str | None = None


class EventReport(StrictModel):
    run_id: NonEmptyString
    events: tuple[RunEvent, ...]
