from pathlib import Path

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.runtime.company_run.engine import execute_company_run
from omx_remote.runtime.runs.run_artifact_store import resolve_run_dir
from omx_remote.schemas.company_run_schemas import (
    COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS,
    CompanyRunArtifactIndex,
    CompanyRunExecutionRequest,
    CompanyRunResult,
    CompanyRunState,
)
from omx_remote.schemas.mcp.omx_agent_tool_schemas import (
    CompanyRunMcpArtifactsPayload,
    CompanyRunMcpExecutePayload,
    CompanyRunMcpStatusPayload,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunCouncilMode,
    CompanyRunTeamLaunchMode,
)
from omx_remote.shared.utils.json_file_store import read_required_json_object
from omx_remote.shared.utils.json_model_dump import model_json_object


def _resolved_cwd(cwd: str | Path) -> Path:
    """Resolve a caller-provided working directory.

    Args:
        cwd [str | Path]: Working directory supplied by CLI or MCP server config.

    Returns:
        Path: Absolute working directory.
    """
    resolved = Path(cwd).expanduser().resolve()
    return resolved


def _resolved_config_path(config_path: str | Path | None) -> Path | None:
    """Resolve an optional command config path.

    Args:
        config_path [str | Path | None]: Optional config path.

    Returns:
        Path | None: Resolved config path when supplied.
    """
    if config_path is None:
        missing_config: None = None
        return missing_config
    resolved = Path(config_path).expanduser().resolve()
    return resolved


def execute_company_run_tool_payload(
    cwd: str | Path,
    objective: str,
    config_path: str | Path | None = None,
    notes: str | None = None,
    live_team_allowed: bool = False,
    council_mode: str = CompanyRunCouncilMode.CODEX.value,
    team_launch_mode: str = CompanyRunTeamLaunchMode.LAUNCH.value,
    worker_count: int = 4,
    timeout_seconds: float = COMPANY_RUN_DEFAULT_TIMEOUT_SECONDS,
) -> JsonObject:
    """Execute company-run through the explicit actual MCP tool.

    Args:
        cwd [str | Path]: Repository root.
        objective [str]: Company-run objective.
        config_path [str | Path | None]: Accepted for parity with preview tools.
        notes [str | None]: Additional operator notes.
        live_team_allowed [bool]: Whether live OMX Team launch is allowed.
        council_mode [str]: Council/subagent execution mode.
        team_launch_mode [str]: Team handling mode.
        worker_count [int]: Team worker count.
        timeout_seconds [float]: Runtime timeout.

    Returns:
        JsonObject: Company-run actual execution payload.
    """
    root = _resolved_cwd(cwd)
    _resolved_config_path(config_path)
    parsed_council_mode = CompanyRunCouncilMode(council_mode)
    parsed_team_launch = CompanyRunTeamLaunchMode(team_launch_mode)
    request = CompanyRunExecutionRequest(
        objective=objective,
        cwd=str(root),
        notes=notes,
        live_team_allowed=live_team_allowed,
        council_mode=parsed_council_mode,
        team_launch_mode=parsed_team_launch,
        worker_count=worker_count,
        timeout_seconds=timeout_seconds,
    )
    result = execute_company_run(request=request)
    typed_payload = CompanyRunMcpExecutePayload(
        ok=True,
        cwd=str(root),
        command_id=result.command_id,
        qualified_id=result.qualified_id,
        dry_run=result.dry_run,
        status=result.status,
        run_id=result.run_id,
        run_dir=result.run_dir,
        result_path=result.result_path,
        company_run_root=result.company_run_root,
        blocked_reasons=result.blocked_reasons,
        team_launch_attempted=result.team_launch_attempted,
        artifacts=result.artifacts,
        warnings=(
            ("Live OMX Team launch was enabled.",)
            if live_team_allowed
            else (
                "Live OMX Team launch was not enabled; Team dispatch evidence was still recorded.",
            )
        ),
    )
    payload = model_json_object(typed_payload)
    return payload


def _load_company_run_result(run_dir: Path) -> CompanyRunResult:
    """Load and validate the known result.json company-run contract.

    Args:
        run_dir [Path]: Actual run directory.

    Returns:
        CompanyRunResult: Validated run result.
    """
    result_payload = read_required_json_object(run_dir / "result.json")
    result = CompanyRunResult.model_validate(result_payload)
    return result


def _load_company_run_state(state_path: Path) -> CompanyRunState:
    """Load and validate the known state.json company-run contract.

    Args:
        state_path [Path]: Company-run state path.

    Returns:
        CompanyRunState: Validated state.
    """
    state_payload = read_required_json_object(state_path)
    state = CompanyRunState.model_validate(state_payload)
    return state


def company_run_status_tool_payload(
    cwd: str | Path,
    run_id: str,
) -> JsonObject:
    """Read status for one company-run actual run.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Actual run id.

    Returns:
        JsonObject: Status payload.
    """
    root = _resolved_cwd(cwd)
    run_dir = resolve_run_dir(root, run_id)
    result = _load_company_run_result(run_dir=run_dir)
    state_path = run_dir / "company-run" / "state.json"
    state = _load_company_run_state(state_path=state_path)
    typed_payload = CompanyRunMcpStatusPayload(
        ok=True,
        cwd=str(root),
        run_id=run_id,
        status=result.status,
        current_phase=str(state.current_phase),
        result_path=str(run_dir / "result.json"),
        state_path=str(state_path),
        company_run_root=str(run_dir / "company-run"),
    )
    payload = model_json_object(typed_payload)
    return payload


def _artifact_index_paths(company_root: Path) -> tuple[Path, ...]:
    """Return artifact paths from the recorded artifact index.

    Args:
        company_root [Path]: Company-run artifact root.

    Returns:
        tuple[Path, ...]: Candidate artifact paths.
    """
    index_path = company_root / "artifact-index.json"
    index_payload = read_required_json_object(index_path)
    index = CompanyRunArtifactIndex.model_validate(index_payload)
    artifact_paths = tuple(Path(path) for path in index.artifact_paths)
    return artifact_paths


def _safe_artifact_file(path: Path, company_root: Path) -> Path | None:
    """Return a safe artifact file path or reject it.

    Args:
        path [Path]: Candidate artifact path.
        company_root [Path]: Company-run artifact root.

    Returns:
        Path | None: Safe file path when it is a regular file inside the root.
    """
    root = company_root.resolve()
    candidate = path if path.is_absolute() else company_root / path
    if candidate.is_symlink():
        missing_path: None = None
        return missing_path
    resolved_candidate = candidate.resolve(strict=False)
    if not resolved_candidate.is_relative_to(root):
        missing_path = None
        return missing_path
    if not candidate.is_file():
        missing_path = None
        return missing_path
    return candidate


def company_run_artifacts_tool_payload(
    cwd: str | Path,
    run_id: str,
) -> JsonObject:
    """Read company-run artifacts for one actual run.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Actual run id.

    Returns:
        JsonObject: Artifact payload.
    """
    root = _resolved_cwd(cwd)
    run_dir = resolve_run_dir(root, run_id)
    company_root = run_dir / "company-run"
    artifacts: dict[str, JsonValue] = {}
    artifact_paths: list[str] = []
    unsafe_artifact_paths: list[str] = []
    for path in _artifact_index_paths(company_root=company_root):
        safe_path = _safe_artifact_file(path=path, company_root=company_root)
        if safe_path is None:
            if path.exists() or path.is_absolute():
                unsafe_artifact_paths.append(str(path))
            continue
        relative_path = str(safe_path.relative_to(run_dir))
        artifact_paths.append(relative_path)
        if safe_path.suffix == ".json":
            artifacts[relative_path] = read_required_json_object(safe_path)
        else:
            artifacts[relative_path] = safe_path.read_text(encoding="utf-8")
    typed_payload = CompanyRunMcpArtifactsPayload(
        ok=True,
        cwd=str(root),
        run_id=run_id,
        company_run_root=str(company_root),
        artifact_paths=tuple(artifact_paths),
        artifacts=artifacts,
        unsafe_artifact_paths=tuple(unsafe_artifact_paths),
    )
    payload = model_json_object(typed_payload)
    return payload
