from pathlib import Path

from omx_remote.runtime.commands.planning.command_runtime_options import (
    team_worker_launch_args,
)
from omx_remote.runtime.company_run.artifacts.artifact_writers import write_company_json
from omx_remote.runtime.company_run.team.worker_dispatch import (
    WORKER_BOUNDARY_SUBAGENT_RULE,
    build_worker_dispatch_payload,
)
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunWorkerDispatchPayload,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunTeamLaunchRecord,
    CompanyRunTeamRequest,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunPhaseStatus,
    CompanyRunTeamLaunchStatus,
)


def _team_bootstrap_phase_status(
    team_status: CompanyRunTeamLaunchStatus,
) -> CompanyRunPhaseStatus:
    """Map a Team launch status to the persisted Team bootstrap phase status.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Runtime Team launch outcome.

    Returns:
        CompanyRunPhaseStatus: Phase ledger status.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        return CompanyRunPhaseStatus.COMPLETE
    if team_status == CompanyRunTeamLaunchStatus.FAILED:
        return CompanyRunPhaseStatus.BLOCKED
    return CompanyRunPhaseStatus.REQUIRES_AGENT_ACTION


def _team_bootstrap_phase_blockers(
    team_record: CompanyRunTeamLaunchRecord,
) -> tuple[str, ...]:
    """Return bootstrap phase blockers derived from the Team launch record.

    Args:
        team_record [CompanyRunTeamLaunchRecord]: Team launch record.

    Returns:
        tuple[str, ...]: Blockers to persist on non-complete phase records.
    """
    if team_record.status == CompanyRunTeamLaunchStatus.COMPLETED:
        return ()
    return (team_record.note,)


def _blocked_team_record(
    company_root: Path,
    request: CompanyRunTeamRequest,
    blockers: tuple[str, ...],
) -> CompanyRunTeamLaunchRecord:
    """Write worker dispatches and return a blocked Team launch record.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.
        blockers [tuple[str, ...]]: Gate blockers preventing Team launch.

    Returns:
        CompanyRunTeamLaunchRecord: Team launch record with follow-up status.
    """
    dispatch_path = company_root / "team" / "worker-dispatches.json"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_payload = CompanyRunWorkerDispatchPayload(
        workers=(),
        blocked_reasons=blockers,
    )
    write_company_json(dispatch_path, dispatch_payload)
    record = CompanyRunTeamLaunchRecord(
        status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
        command=request.native_argv,
        runtime_options=request.runtime_options,
        worker_launch_args=team_worker_launch_args(
            runtime_options=request.runtime_options,
        ),
        worker_count=request.worker_count,
        dispatch_path=str(dispatch_path),
        launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
        launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
        note="Team launch blocked by company-run readiness gates: "
        + "; ".join(blockers),
    )
    return record


def _write_team_dispatch_packets(
    company_root: Path,
    request: CompanyRunTeamRequest,
) -> Path:
    """Write one ownership dispatch packet per requested Team worker.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.

    Returns:
        Path: Worker dispatch artifact path.
    """
    dispatch_path = company_root / "team" / "worker-dispatches.json"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_payload = build_worker_dispatch_payload(
        objective=request.objective,
        worker_count=request.worker_count,
        allowed_subagents=("executor", "test-engineer", "code-reviewer"),
        subagent_rule=WORKER_BOUNDARY_SUBAGENT_RULE,
    )
    write_company_json(dispatch_path, dispatch_payload)
    return dispatch_path


def _planned_team_record(
    company_root: Path,
    request: CompanyRunTeamRequest,
) -> CompanyRunTeamLaunchRecord:
    """Write scoped worker dispatches for a gated Team handoff.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.

    Returns:
        CompanyRunTeamLaunchRecord: Team launch record requiring follow-up.
    """
    dispatch_path = _write_team_dispatch_packets(
        company_root=company_root,
        request=request,
    )
    record = _team_launch_record_from_dispatch(
        company_root=company_root,
        request=request,
        dispatch_path=dispatch_path,
        note="Team dispatch packets written; live Team launch not allowed for this request.",
    )
    return record


def _team_launch_record_from_dispatch(
    company_root: Path,
    request: CompanyRunTeamRequest,
    dispatch_path: Path,
    note: str,
) -> CompanyRunTeamLaunchRecord:
    """Build the Team launch record after worker dispatch packets exist.

    Args:
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunTeamRequest]: Team launch request.
        dispatch_path [Path]: Existing worker-dispatches artifact path.
        note [str]: Status note for the launch record.

    Returns:
        CompanyRunTeamLaunchRecord: Team launch record requiring follow-up.
    """
    record = CompanyRunTeamLaunchRecord(
        status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
        command=request.native_argv,
        runtime_options=request.runtime_options,
        worker_launch_args=team_worker_launch_args(
            runtime_options=request.runtime_options,
        ),
        worker_count=request.worker_count,
        dispatch_path=str(dispatch_path),
        launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
        launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
        note=note,
    )
    return record

