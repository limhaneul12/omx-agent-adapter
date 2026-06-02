from collections.abc import Callable
from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.company_run.artifacts.artifact_writers import (
    artifact_record,
    write_company_json,
)
from omx_remote.runtime.company_run.artifacts.phase_log import (
    append_company_run_phase,
)
from omx_remote.runtime.company_run.governance.phase_gates import (
    validate_phase_gate_order,
    validate_team_bootstrap_readiness,
)
from omx_remote.runtime.company_run.team.team_bootstrap_readiness import (
    _team_bootstrap_artifact_evidence,
    _team_bootstrap_vote_evidence,
)
from omx_remote.runtime.company_run.team.team_launch_records import (
    _blocked_team_record,
    _planned_team_record,
    _team_bootstrap_phase_blockers,
    _team_bootstrap_phase_status,
    _team_launch_record_from_dispatch,
    _write_team_dispatch_packets,
)
from omx_remote.runtime.company_run.team.team_runtime import (
    launch_company_run_team,
)
from omx_remote.runtime.company_run.team.team_task_prompt import (
    build_team_task,
)
from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunPhaseRecord,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunExecutionRequest,
    CompanyRunTeamLaunchRecord,
    CompanyRunTeamRequest,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunPhase,
)

TeamLauncher = Callable[[CompanyRunTeamRequest], object]

def run_team_gate_for_company_run(
    paths: ActualRunPaths,
    cwd: Path,
    company_root: Path,
    request: CompanyRunExecutionRequest,
    live_team_allowed: bool,
    phase_records: list[CompanyRunPhaseRecord],
    team_launcher: TeamLauncher | None,
) -> CompanyRunTeamLaunchRecord:
    """Record or launch the mandatory Team bootstrap gate.

    Args:
        paths [ActualRunPaths]: Actual-run artifact paths for launch attempts.
        cwd [Path]: Repository root that company-run operates on.
        company_root [Path]: Directory that owns company-run artifacts.
        request [CompanyRunExecutionRequest]: Company-run request.
        live_team_allowed [bool]: Whether native OMX Team launch may run now.
        phase_records [list[CompanyRunPhaseRecord]]: Mutable phase log.
        team_launcher [TeamLauncher | None]: Optional injected Team launcher.

    Returns:
        CompanyRunTeamLaunchRecord: Persisted Team launch record.
    """
    team_task = build_team_task(
        objective=request.objective,
        company_root=company_root,
        worker_count=request.worker_count,
        runtime_options=request.runtime_options,
    )
    team_request = CompanyRunTeamRequest(
        native_argv=("omx", "team", f"{request.worker_count}:executor", team_task),
        worker_count=request.worker_count,
        objective=request.objective,
        team_task=team_task,
        runtime_options=request.runtime_options,
    )
    completed_phases = tuple(record.phase for record in phase_records)
    order_verdict = validate_phase_gate_order(
        completed_phases=completed_phases,
        next_phase=CompanyRunPhase.TEAM_BOOTSTRAP,
    )
    artifact_evidence = _team_bootstrap_artifact_evidence(company_root=company_root)
    vote_evidence = _team_bootstrap_vote_evidence(company_root=company_root)
    readiness_verdict = validate_team_bootstrap_readiness(
        completed_phases=completed_phases,
        artifacts=artifact_evidence,
        votes=vote_evidence.outcomes,
    )
    if not order_verdict.allowed or not readiness_verdict.allowed:
        blockers = (
            *order_verdict.blocked_reasons,
            *vote_evidence.blocked_reasons,
            *readiness_verdict.blocked_reasons,
        )
        team_record = _blocked_team_record(
            company_root=company_root,
            request=team_request,
            blockers=blockers,
        )
    elif team_launcher is not None:
        dispatch_path = _write_team_dispatch_packets(
            company_root=company_root,
            request=team_request,
        )
        team_launcher(team_request)
        team_record = _team_launch_record_from_dispatch(
            company_root=company_root,
            request=team_request,
            dispatch_path=dispatch_path,
            note="Team dispatch packets were written before the injected Team launcher callback.",
        )
    elif live_team_allowed or str(request.team_launch_mode) == "handoff":
        team_record, _ = launch_company_run_team(
            paths=paths,
            cwd=cwd,
            objective=request.objective,
            company_root=company_root,
            worker_count=request.worker_count,
            timeout_seconds=request.timeout_seconds,
            step_index=2,
            launch_mode=str(request.team_launch_mode),
            runtime_options=request.runtime_options,
        )
    else:
        team_record = _planned_team_record(
            company_root=company_root,
            request=team_request,
        )
    team_launch_path = company_root / "implementation" / "team-launch.json"
    write_company_json(team_launch_path, team_record)
    phase_status = _team_bootstrap_phase_status(team_status=team_record.status)
    phase_blockers = _team_bootstrap_phase_blockers(team_record=team_record)
    append_company_run_phase(
        phase_records=phase_records,
        phase=CompanyRunPhase.TEAM_BOOTSTRAP,
        summary=f"Team bootstrap recorded with status {team_record.status}.",
        artifacts=(
            artifact_record(
                kind=CompanyRunArtifactKind.TEAM,
                path=Path(team_record.dispatch_path),
            ),
            artifact_record(kind=CompanyRunArtifactKind.TEAM, path=team_launch_path),
        ),
        status=phase_status,
        blocked_reasons=phase_blockers,
    )
    return team_record
