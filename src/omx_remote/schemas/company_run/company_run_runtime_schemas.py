from pydantic import ConfigDict, Field

from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel
from omx_remote.schemas.company_run.company_run_core_schemas import (
    CompanyRunArtifactRecord,
    CompanyRunRoster,
)
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunPhaseRecord,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunCouncilMode,
    CompanyRunFinalStatus,
    CompanyRunPhase,
    CompanyRunTeamLaunchMode,
    CompanyRunTeamLaunchStatus,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import DiscoveryGateProfile

COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS = 1800.0


class CompanyRunTeamLaunchRecord(StrictSchemaModel):
    """OMX Team launch and optional await evidence for company-run."""

    status: CompanyRunTeamLaunchStatus
    command: tuple[NonEmptyString, ...]
    runtime_options: CommandRuntimeOptions | None = None
    worker_launch_args: NonEmptyString | None = None
    worker_count: int = Field(ge=3)
    team_name: NonEmptyString | None = None
    dispatch_path: NonEmptyString
    launch_stdout_path: NonEmptyString
    launch_stderr_path: NonEmptyString
    await_stdout_path: NonEmptyString | None = None
    await_stderr_path: NonEmptyString | None = None
    exit_code: int | None = None
    await_exit_code: int | None = None
    note: NonEmptyString


class CompanyRunNativeTeamTaskCounts(StrictSchemaModel):
    """Task counters returned by `omx team status --json`."""

    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    blocked: int = Field(ge=0)
    in_progress: int = Field(ge=0)
    completed: int = Field(ge=0)
    failed: int = Field(ge=0)


class CompanyRunNativeTeamWorkerCounts(StrictSchemaModel):
    """Worker counters returned by `omx team status --json`."""

    total: int = Field(ge=0)
    dead: int = Field(ge=0)
    non_reporting: int = Field(ge=0)


class CompanyRunNativeTeamStatusSnapshot(StrictSchemaModel):
    """Typed subset of `omx team status --json` used for completion evidence."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )

    team_name: NonEmptyString
    status: NonEmptyString
    phase: NonEmptyString | None = None
    tasks: CompanyRunNativeTeamTaskCounts | None = None
    workers: CompanyRunNativeTeamWorkerCounts | None = None


class CompanyRunNativeTeamListTasksRequest(StrictSchemaModel):
    """Input payload for `omx team api list-tasks` owner-distribution evidence."""

    team_name: NonEmptyString


class CompanyRunNativeTeamTaskState(StrictSchemaModel):
    """Typed subset of one native OMX Team task record."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )

    id: NonEmptyString
    status: NonEmptyString
    owner: NonEmptyString | None = None


class CompanyRunNativeTeamTaskListData(StrictSchemaModel):
    """Typed subset of `omx team api list-tasks` data."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )

    count: int = Field(ge=0)
    tasks: tuple[CompanyRunNativeTeamTaskState, ...]


class CompanyRunNativeTeamTaskListResponse(StrictSchemaModel):
    """Typed subset of `omx team api list-tasks --json` response."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )

    ok: bool
    data: CompanyRunNativeTeamTaskListData


class CompanyRunState(StrictSchemaModel):
    """Persisted state snapshot for one actual company-run execution."""

    run_id: NonEmptyString
    objective: NonEmptyString
    cwd: NonEmptyString
    runtime_options: CommandRuntimeOptions | None = None
    status: CompanyRunFinalStatus
    current_phase: CompanyRunPhase
    roster: CompanyRunRoster
    phases: tuple[CompanyRunPhaseRecord, ...]
    votes: tuple[CompanyRunVoteRecord, ...]
    artifacts: tuple[CompanyRunArtifactRecord, ...]
    team_launch: CompanyRunTeamLaunchRecord | None = None
    alexandria_tool_points: tuple[NonEmptyString, ...]
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CompanyRunExecutionSummary(StrictSchemaModel):
    """Small MCP-friendly company-run execution/status summary."""

    run_id: NonEmptyString
    status: CompanyRunFinalStatus
    state_path: NonEmptyString
    artifact_index_path: NonEmptyString
    company_run_root: NonEmptyString
    team_status: CompanyRunTeamLaunchStatus | None = None
    blocked_reasons: tuple[NonEmptyString, ...] = ()


class CompanyRunExecutionRequest(StrictSchemaModel):
    """Public request contract for actual company-run execution."""

    objective: NonEmptyString
    cwd: NonEmptyString
    autonomy: NonEmptyString = "agent"
    notes: NonEmptyString | None = None
    council_mode: CompanyRunCouncilMode = CompanyRunCouncilMode.CODEX
    live_team_allowed: bool = False
    team_launch_mode: CompanyRunTeamLaunchMode = CompanyRunTeamLaunchMode.LAUNCH
    worker_count: int = Field(ge=3, default=4)
    max_research_rounds: int = Field(ge=1, default=2)
    discovery_profile: DiscoveryGateProfile = DiscoveryGateProfile.STANDARD
    max_discovery_questions: int | None = Field(ge=1, default=None)
    budget_hint: NonEmptyString | None = None
    runtime_options: CommandRuntimeOptions | None = None
    timeout_seconds: float = Field(
        ge=1.0,
        default=COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS,
    )


class CompanyRunTeamRequest(StrictSchemaModel):
    """Injected Team launcher request for company-run engine tests and runtime."""

    native_argv: tuple[NonEmptyString, ...]
    worker_count: int = Field(ge=3)
    objective: NonEmptyString
    team_task: NonEmptyString
    runtime_options: CommandRuntimeOptions | None = None


class CompanyRunCouncilPromptContext(StrictSchemaModel):
    """Template context for one-company-run council prompt asset."""

    role: NonEmptyString
    objective: NonEmptyString
    artifact_label: NonEmptyString
    required_points: NonEmptyString


class CompanyRunTeamPromptContext(StrictSchemaModel):
    """Template context for the company-run Team task prompt asset."""

    objective: NonEmptyString
    worker_count: NonEmptyString
    owner_matrix: NonEmptyString
    company_root: NonEmptyString
    prd_path: NonEmptyString
    test_spec_path: NonEmptyString
    execution_brief_path: NonEmptyString
    kickoff_path: NonEmptyString
    dispatch_path: NonEmptyString
    runtime_options: NonEmptyString


class CompanyRunResultMetadata(StrictSchemaModel):
    """Typed metadata paths attached to a company-run result."""

    state_path: NonEmptyString
    artifact_index_path: NonEmptyString
    discovery_decision_report_path: NonEmptyString | None = None


class CompanyRunResult(StrictSchemaModel):
    """MCP-friendly actual company-run execution result."""

    run_id: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    cwd: NonEmptyString
    dry_run: bool
    runtime_options: CommandRuntimeOptions | None = None
    status: NonEmptyString
    run_dir: NonEmptyString
    result_path: NonEmptyString
    company_run_root: NonEmptyString
    blocked_reasons: tuple[NonEmptyString, ...]
    team_launch_attempted: bool
    team_task: NonEmptyString | None
    artifacts: tuple[NonEmptyString, ...]
    metadata: CompanyRunResultMetadata


class CompanyRunRecordPayload(StrictSchemaModel):
    """Typed payload for the run-level company-run run record file."""

    run_id: NonEmptyString
    command_id: NonEmptyString
    qualified_id: NonEmptyString
    cwd: NonEmptyString
    dry_run: bool
    status: NonEmptyString
    started_at: NonEmptyString
    finished_at: NonEmptyString
    artifacts: tuple[NonEmptyString, ...]
