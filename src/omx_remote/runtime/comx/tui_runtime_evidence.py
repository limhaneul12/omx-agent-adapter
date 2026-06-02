from pathlib import Path

from pydantic import ValidationError

from omx_remote.schemas.company_run_schemas import CompanyRunWorkerDispatchPayload
from omx_remote.schemas.comx.tui_schemas import ComxTuiRuntimeEvidenceSummary

RUN_ARTIFACT_ROOT = ".comx-agent/runs"
COMPANY_RUN_DIR_NAME = "company-run"
MAX_ARTIFACT_REFERENCES = 5


def _company_run_artifact_dirs(workspace: Path) -> tuple[Path, ...]:
    """Find company-run artifact directories under the workspace.

    Args:
        workspace [Path]: Repository root to inspect.

    Returns:
        tuple[Path, ...]: Company-run artifact directories ordered newest first.
    """
    run_root: Path = workspace / RUN_ARTIFACT_ROOT
    if not run_root.exists():
        empty_dirs: tuple[Path, ...] = ()
        return empty_dirs

    artifact_dirs: list[Path] = []
    for run_dir in sorted(run_root.iterdir()):
        company_run_dir: Path = run_dir / COMPANY_RUN_DIR_NAME
        if company_run_dir.is_dir():
            artifact_dirs.append(company_run_dir)

    ordered_dirs: tuple[Path, ...] = tuple(reversed(artifact_dirs))
    return ordered_dirs


def _relative_artifact_path(workspace: Path, artifact_path: Path) -> str:
    """Render an artifact path relative to the workspace when possible.

    Args:
        workspace [Path]: Repository root used as the display base.
        artifact_path [Path]: Artifact path to display.

    Returns:
        str: Relative display path or absolute fallback.
    """
    try:
        relative_path: str = str(artifact_path.relative_to(workspace))
    except ValueError:
        relative_path = str(artifact_path)
    return relative_path


def _artifact_references(workspace: Path, company_run_dir: Path) -> tuple[str, ...]:
    """Collect a bounded list of important artifact references.

    Args:
        workspace [Path]: Repository root used as the display base.
        company_run_dir [Path]: Latest company-run artifact directory.

    Returns:
        tuple[str, ...]: Bounded artifact reference paths.
    """
    preferred_paths: tuple[Path, ...] = (
        company_run_dir / "planning" / "prd.md",
        company_run_dir / "planning" / "test-spec.md",
        company_run_dir / "planning" / "execution-brief.md",
        company_run_dir / "memory-recall.md",
        company_run_dir / "team" / "worker-dispatches.json",
    )
    references: list[str] = []
    for artifact_path in preferred_paths:
        if artifact_path.exists():
            references.append(_relative_artifact_path(workspace, artifact_path))
        if len(references) >= MAX_ARTIFACT_REFERENCES:
            break
    result: tuple[str, ...] = tuple(references)
    return result


def _artifact_count(company_run_dir: Path) -> int:
    """Count files in one company-run artifact directory.

    Args:
        company_run_dir [Path]: Company-run artifact directory to count.

    Returns:
        int: Number of files under the artifact directory.
    """
    count: int = sum(
        1 for artifact_path in company_run_dir.rglob("*") if artifact_path.is_file()
    )
    return count


def _team_worker_count(dispatch_path: Path, warnings: list[str]) -> int:
    """Read worker count from a worker-dispatches artifact.

    Args:
        dispatch_path [Path]: Worker dispatch artifact path.
        warnings [list[str]]: Mutable warnings collection for degraded reads.

    Returns:
        int: Worker count recorded by the dispatch artifact.
    """
    if not dispatch_path.exists():
        missing_count: int = 0
        return missing_count

    try:
        payload = CompanyRunWorkerDispatchPayload.model_validate_json(
            dispatch_path.read_bytes()
        )
    except ValidationError:
        warnings.append(f"unreadable team dispatch artifact: {dispatch_path}")
        unreadable_count: int = 0
        return unreadable_count

    worker_count: int = len(payload.workers)
    return worker_count


def build_tui_runtime_evidence_summary(
    cwd: str | Path,
    command_recipe_count: int,
) -> ComxTuiRuntimeEvidenceSummary:
    """Build typed runtime evidence for COMX TUI status panels.

    Args:
        cwd [str | Path]: Repository root to inspect.
        command_recipe_count [int]: Count of composed command recipes already loaded.

    Returns:
        ComxTuiRuntimeEvidenceSummary: Normalized status/artifact/team/memory evidence.
    """
    workspace: Path = Path(cwd)
    warnings: list[str] = []
    company_run_dirs: tuple[Path, ...] = _company_run_artifact_dirs(workspace)
    if not company_run_dirs:
        summary = ComxTuiRuntimeEvidenceSummary(
            latest_run_id=None,
            artifact_count=0,
            artifact_references=(),
            memory_recall_path=None,
            team_dispatch_path=None,
            team_worker_count=0,
            command_recipe_count=command_recipe_count,
            warnings=("no .comx-agent company-run artifacts found",),
        )
        return summary

    latest_company_run_dir: Path = company_run_dirs[0]
    latest_run_id: str = latest_company_run_dir.parent.name
    memory_recall_path: Path = latest_company_run_dir / "memory-recall.md"
    team_dispatch_path: Path = (
        latest_company_run_dir / "team" / "worker-dispatches.json"
    )
    team_worker_count: int = _team_worker_count(team_dispatch_path, warnings)
    memory_recall_display: str | None = None
    if memory_recall_path.exists():
        memory_recall_display = _relative_artifact_path(workspace, memory_recall_path)
    team_dispatch_display: str | None = None
    if team_dispatch_path.exists():
        team_dispatch_display = _relative_artifact_path(workspace, team_dispatch_path)

    summary = ComxTuiRuntimeEvidenceSummary(
        latest_run_id=latest_run_id,
        artifact_count=_artifact_count(latest_company_run_dir),
        artifact_references=_artifact_references(workspace, latest_company_run_dir),
        memory_recall_path=memory_recall_display,
        team_dispatch_path=team_dispatch_display,
        team_worker_count=team_worker_count,
        command_recipe_count=command_recipe_count,
        warnings=tuple(warnings),
    )
    return summary


def format_tui_runtime_evidence_summary(
    summary: ComxTuiRuntimeEvidenceSummary,
) -> tuple[str, ...]:
    """Format runtime evidence summary lines for TUI rendering.

    Args:
        summary [ComxTuiRuntimeEvidenceSummary]: Typed runtime evidence summary.

    Returns:
        tuple[str, ...]: Human-readable status lines.
    """
    latest_run: str = summary.latest_run_id or "none"
    memory_path: str = summary.memory_recall_path or "missing"
    team_path: str = summary.team_dispatch_path or "missing"
    lines: list[str] = [
        "runtime_evidence:",
        f"  latest_run: {latest_run}",
        f"  artifacts: {summary.artifact_count}",
        f"  memory_recall: {memory_path}",
        f"  team_dispatch: {team_path}",
        f"  team_workers: {summary.team_worker_count}",
        f"  command_recipes: {summary.command_recipe_count}",
    ]
    if summary.artifact_references:
        artifact_text: str = ", ".join(summary.artifact_references)
        lines.append(f"  artifact_refs: {artifact_text}")
    lines.extend(f"  warning: {warning}" for warning in summary.warnings)
    result: tuple[str, ...] = tuple(lines)
    return result
