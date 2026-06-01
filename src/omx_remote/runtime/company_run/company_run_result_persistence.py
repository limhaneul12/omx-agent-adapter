from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.company_run.artifact_index import (
    build_company_run_artifact_index,
)
from omx_remote.runtime.company_run.company_run_artifacts import artifact_record
from omx_remote.schemas.company_run_schemas import (
    CompanyRunArtifactRecord,
    CompanyRunArtifactSummaryPayload,
    CompanyRunExecutionRequest,
    CompanyRunRecordPayload,
    CompanyRunResult,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunArtifactKind,
    CompanyRunFinalStatus,
    CompanyRunTeamLaunchStatus,
)
from omx_remote.shared.utils.runtime_identity import utcnow_text


def actual_company_run_paths(run_id: str, run_dir: Path) -> ActualRunPaths:
    """Build actual-run path bundle for the company-run engine.

    Args:
        run_id [str]: Actual run id.
        run_dir [Path]: Actual run directory.

    Returns:
        ActualRunPaths: Actual run path bundle.
    """
    paths = ActualRunPaths(
        run_id=run_id,
        run_dir=run_dir,
        plan_path=run_dir / "plan.json",
        run_record_path=run_dir / "run.json",
        autonomy_decision_path=run_dir / "autonomy-decision.json",
        result_path=run_dir / "result.json",
        artifacts_path=run_dir / "artifacts.json",
        recovery_path=run_dir / "recovery.md",
        handoff_path=run_dir / "handoff.md",
        stdout_log_path=run_dir / "stdout.log",
        stderr_log_path=run_dir / "stderr.log",
    )
    return paths


def write_initial_company_run_files(
    paths: ActualRunPaths, request: CompanyRunExecutionRequest
) -> None:
    """Write initial run files before company-run phases start.

    Args:
        paths [ActualRunPaths]: Actual run paths.
        request [CompanyRunExecutionRequest]: Execution request.
    """
    for path in (
        paths.recovery_path,
        paths.handoff_path,
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")
    write_redacted_json_artifact(paths.plan_path, request)


def write_final_company_run_files(
    paths: ActualRunPaths,
    result: CompanyRunResult,
    artifact_index_path: Path,
) -> None:
    """Persist final company-run result, artifact summary, handoff, and run record.

    Args:
        paths [ActualRunPaths]: Actual run paths.
        result [CompanyRunResult]: Final company-run result.
        artifact_index_path [Path]: Artifact index path.
    """
    write_redacted_json_artifact(paths.result_path, result)
    artifact_summary = CompanyRunArtifactSummaryPayload(
        artifact_index_path=str(artifact_index_path),
        artifacts=result.artifacts,
    )
    write_redacted_json_artifact(
        paths.artifacts_path,
        artifact_summary,
    )
    paths.handoff_path.write_text(
        f"# company-run {result.run_id}\n\nstatus: {result.status}\ncompany_run_root: {result.company_run_root}\n",
        encoding="utf-8",
    )
    timestamp = utcnow_text()
    run_record = CompanyRunRecordPayload(
        run_id=result.run_id,
        command_id=result.command_id,
        qualified_id=result.qualified_id,
        cwd=result.cwd,
        dry_run=result.dry_run,
        status=result.status,
        started_at=timestamp,
        finished_at=timestamp,
        artifacts=result.artifacts,
    )
    write_redacted_json_artifact(
        paths.run_record_path,
        run_record,
    )


def company_run_artifact_records(
    company_root: Path,
) -> tuple[CompanyRunArtifactRecord, ...]:
    """Build records for every required company-run artifact path.

    Args:
        company_root [Path]: Company-run artifact root.

    Returns:
        tuple[CompanyRunArtifactRecord, ...]: Required artifact records.
    """
    index = build_company_run_artifact_index(company_root.parent)
    records = tuple(
        record_for_company_run_path(Path(path)) for path in index.artifact_paths
    )
    return records


def record_for_company_run_path(path: Path) -> CompanyRunArtifactRecord:
    """Build one typed company-run artifact record from a path.

    Args:
        path [Path]: Artifact path.

    Returns:
        CompanyRunArtifactRecord: Artifact record.
    """
    kind = artifact_kind_for_path(path)
    record = artifact_record(kind, path)
    return record


def artifact_kind_for_path(path: Path) -> CompanyRunArtifactKind:
    """Infer a company-run artifact kind from its owned path.

    Args:
        path [Path]: Artifact path.

    Returns:
        CompanyRunArtifactKind: Inferred artifact kind.
    """
    path_text = str(path)
    if "/discovery/" in path_text:
        return CompanyRunArtifactKind.DISCOVERY
    if "decision-report" in path_text:
        return CompanyRunArtifactKind.DECISION_REPORT
    if "/research/" in path_text:
        return CompanyRunArtifactKind.RESEARCH
    if "/planning/" in path_text:
        if path.name == "prd.md":
            return CompanyRunArtifactKind.PRD
        if path.name == "test-spec.md":
            return CompanyRunArtifactKind.TEST_SPEC
        if path.name == "execution-brief.md":
            return CompanyRunArtifactKind.EXECUTION_BRIEF
        return CompanyRunArtifactKind.READINESS
    if "/team/" in path_text or "/implementation/" in path_text:
        return CompanyRunArtifactKind.TEAM
    if "/review/" in path_text:
        return CompanyRunArtifactKind.REVIEW
    if "/release/" in path_text:
        return CompanyRunArtifactKind.RELEASE
    if "vote" in path_text:
        return CompanyRunArtifactKind.VOTE
    if "memory" in path_text:
        return CompanyRunArtifactKind.MEMORY
    return CompanyRunArtifactKind.STATE


def artifact_kind_for_planning_file(filename: str) -> CompanyRunArtifactKind:
    """Return artifact kind for one planning artifact filename.

    Args:
        filename [str]: Planning artifact filename.

    Returns:
        CompanyRunArtifactKind: Planning artifact kind.
    """
    if filename == "prd.md":
        return CompanyRunArtifactKind.PRD
    if filename == "test-spec.md":
        return CompanyRunArtifactKind.TEST_SPEC
    if filename == "execution-brief.md":
        return CompanyRunArtifactKind.EXECUTION_BRIEF
    return CompanyRunArtifactKind.READINESS


def final_status_from_team(
    team_status: CompanyRunTeamLaunchStatus,
) -> CompanyRunFinalStatus:
    """Map Team launch status to company-run final status.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch status.

    Returns:
        CompanyRunFinalStatus: Final company-run status.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        return CompanyRunFinalStatus.SUCCEEDED
    if team_status == CompanyRunTeamLaunchStatus.FAILED:
        return CompanyRunFinalStatus.FAILED
    return CompanyRunFinalStatus.REQUIRES_AGENT_ACTION


def blocked_reasons_from_team(
    team_status: CompanyRunTeamLaunchStatus,
) -> tuple[str, ...]:
    """Return final blockers implied by Team status.

    Args:
        team_status [CompanyRunTeamLaunchStatus]: Team launch status.

    Returns:
        tuple[str, ...]: Final blocked reasons.
    """
    if team_status == CompanyRunTeamLaunchStatus.COMPLETED:
        return ()
    if team_status == CompanyRunTeamLaunchStatus.FAILED:
        return ("OMX Team launch failed; inspect team-launch artifacts.",)
    return ("OMX Team follow-up is required before release can be claimed.",)


def alexandria_tool_points() -> tuple[str, ...]:
    """Return concrete Alexandria MCP tool points recorded by company-run.

    Returns:
        tuple[str, ...]: Concrete Alexandria MCP tool points.
    """
    points = (
        "alexandria_search_vault for prior company-run/project intent",
        "alexandria_read_note for selected prior decisions",
        "alexandria_get_current_memory_compact for context recovery",
        "alexandria_save_note for verified closeout memory",
    )
    return points
