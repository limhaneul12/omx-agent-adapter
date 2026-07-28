from __future__ import annotations

from collections.abc import Mapping

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel
from comx_harness.shared.harness_enums.operator_enums import AgentStatus
from pydantic import BaseModel, ConfigDict, Field


class OmxExternalModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class OmxApiFailure(OmxExternalModel):
    code: str
    message: str


class OmxNativeWorkerInfo(OmxExternalModel):
    name: str
    index: int
    role: str
    assigned_tasks: tuple[str, ...] = ()
    pid: int | None = None
    pane_id: str | None = None
    working_dir: str | None = None
    worktree_path: str | None = None
    worktree_branch: str | None = None


class OmxNativeTeamConfig(OmxExternalModel):
    name: str
    task: str
    worker_count: int = 0
    workers: tuple[OmxNativeWorkerInfo, ...] = ()
    created_at: str | None = None
    tmux_session: str | None = None
    leader_pane_id: str | None = None
    workspace_mode: str | None = None


class OmxNativeTask(OmxExternalModel):
    id: str
    subject: str
    description: str = ""
    status: str
    role: str | None = None
    owner: str | None = None
    result: str | None = None
    error: str | None = None
    blocked_by: tuple[str, ...] = ()
    created_at: str | None = None
    completed_at: str | None = None


class OmxNativeTaskCounts(OmxExternalModel):
    total: int = 0
    pending: int = 0
    blocked: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0


class OmxNativeSummaryWorker(OmxExternalModel):
    name: str
    alive: bool
    last_turn_at: str | None = Field(default=None, alias="lastTurnAt")
    turns_without_progress: int = Field(default=0, alias="turnsWithoutProgress")


class OmxNativeTeamSummary(OmxExternalModel):
    team_name: str = Field(alias="teamName")
    worker_count: int = Field(default=0, alias="workerCount")
    tasks: OmxNativeTaskCounts = Field(default_factory=OmxNativeTaskCounts)
    workers: tuple[OmxNativeSummaryWorker, ...] = ()
    non_reporting_workers: tuple[str, ...] = Field(
        default=(), alias="nonReportingWorkers"
    )


class OmxNativeMonitorSnapshot(OmxExternalModel):
    worker_alive_by_name: Mapping[str, bool] = Field(
        default_factory=dict, alias="workerAliveByName"
    )
    worker_state_by_name: Mapping[str, str] = Field(
        default_factory=dict, alias="workerStateByName"
    )
    worker_turn_count_by_name: Mapping[str, int] = Field(
        default_factory=dict, alias="workerTurnCountByName"
    )
    worker_task_id_by_name: Mapping[str, str] = Field(
        default_factory=dict, alias="workerTaskIdByName"
    )
    task_status_by_id: Mapping[str, str] = Field(
        default_factory=dict, alias="taskStatusById"
    )


class OmxConfigData(OmxExternalModel):
    config: OmxNativeTeamConfig


class OmxConfigEnvelope(OmxExternalModel):
    ok: bool
    operation: str
    data: OmxConfigData | None = None
    error: OmxApiFailure | None = None


class OmxTasksData(OmxExternalModel):
    count: int = 0
    tasks: tuple[OmxNativeTask, ...] = ()


class OmxTasksEnvelope(OmxExternalModel):
    ok: bool
    operation: str
    data: OmxTasksData | None = None
    error: OmxApiFailure | None = None


class OmxSummaryData(OmxExternalModel):
    summary: OmxNativeTeamSummary


class OmxSummaryEnvelope(OmxExternalModel):
    ok: bool
    operation: str
    data: OmxSummaryData | None = None
    error: OmxApiFailure | None = None


class OmxMonitorData(OmxExternalModel):
    snapshot: OmxNativeMonitorSnapshot | None = None


class OmxMonitorEnvelope(OmxExternalModel):
    ok: bool
    operation: str
    data: OmxMonitorData | None = None
    error: OmxApiFailure | None = None


class OmxTeamStatusEnvelope(OmxExternalModel):
    team_name: str
    status: str


class OmxWorkerProjection(StrictModel):
    name: NonEmptyString
    role: NonEmptyString
    state: AgentStatus = AgentStatus.UNKNOWN
    alive: bool | None = None
    current_task_id: NonEmptyString | None = None
    pane_id: NonEmptyString | None = None
    working_dir: NonEmptyString | None = None
    worktree_path: NonEmptyString | None = None
    worktree_branch: NonEmptyString | None = None
    last_turn_at: NonEmptyString | None = None
    turns_without_progress: int = Field(default=0, ge=0)
    attention: tuple[NonEmptyString, ...] = ()


class OmxTaskProjection(StrictModel):
    task_id: NonEmptyString
    subject: NonEmptyString
    status: NonEmptyString
    owner: NonEmptyString | None = None
    role: NonEmptyString | None = None
    blocked_by: tuple[NonEmptyString, ...] = ()
    error: NonEmptyString | None = None


class OmxTeamProjection(StrictModel):
    team_name: NonEmptyString
    status: NonEmptyString
    available: bool
    detail: NonEmptyString
    task: NonEmptyString | None = None
    tmux_session: NonEmptyString | None = None
    leader_pane_id: NonEmptyString | None = None
    workspace_mode: NonEmptyString | None = None
    workers: tuple[OmxWorkerProjection, ...] = ()
    tasks: tuple[OmxTaskProjection, ...] = ()
    non_reporting_workers: tuple[NonEmptyString, ...] = ()
    attention: tuple[NonEmptyString, ...] = ()
