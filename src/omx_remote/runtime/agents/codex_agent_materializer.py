from hashlib import sha256
from pathlib import Path

from omx_remote.runtime.agents.codex_agent_materialization_plan import (
    build_codex_agent_materialization_plan,
)
from omx_remote.schemas.agents.codex_agent_materialization_schemas import (
    CodexAgentMaterializationApplyResult,
    CodexAgentMaterializationFile,
    CodexAgentMaterializationFileStatus,
    CodexAgentMaterializationPlan,
    CodexAgentMaterializationStatus,
)


def apply_codex_agent_materialization(
    plan: CodexAgentMaterializationPlan,
    dry_run: bool,
) -> CodexAgentMaterializationApplyResult:
    """Apply a Codex agent materialization plan.

    Args:
        plan [CodexAgentMaterializationPlan]: Plan to apply.
        dry_run [bool]: Whether to avoid writing files.

    Returns:
        CodexAgentMaterializationApplyResult: Apply result.
    """
    written_files: list[str] = []
    if not dry_run and plan.supported:
        for planned_file in plan.files:
            target_path: Path = Path(planned_file.target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(planned_file.content, encoding="utf-8")
            written_files.append(str(target_path))

    result = CodexAgentMaterializationApplyResult(
        dry_run=dry_run,
        plan=plan,
        written_files=tuple(written_files),
        warnings=plan.warnings,
    )
    return result


def _actual_sha256(path: Path) -> str | None:
    """Hash an existing generated file.

    Args:
        path [Path]: File path to hash.

    Returns:
        str | None: SHA-256 digest when the file exists.
    """
    if not path.exists():
        missing_digest: None = None
        return missing_digest

    digest: str = sha256(path.read_bytes()).hexdigest()
    return digest


def _file_status(
    planned_file: CodexAgentMaterializationFile,
) -> CodexAgentMaterializationFileStatus:
    """Build status for one planned generated file.

    Args:
        planned_file [CodexAgentMaterializationFile]: Planned file to inspect.

    Returns:
        CodexAgentMaterializationFileStatus: Generated file status.
    """
    target_path: Path = Path(planned_file.target_path)
    actual_sha256: str | None = _actual_sha256(target_path)
    exists: bool = actual_sha256 is not None
    matches: bool = actual_sha256 == planned_file.content_sha256
    status = CodexAgentMaterializationFileStatus(
        agent_id=planned_file.agent_id,
        target_path=planned_file.target_path,
        exists=exists,
        matches=matches,
        expected_sha256=planned_file.content_sha256,
        actual_sha256=actual_sha256,
    )
    return status


def read_codex_agent_materialization_status(
    cwd: str | Path,
    codex_home: str | Path | None = None,
) -> CodexAgentMaterializationStatus:
    """Read whether generated Codex agent files match the TOML source.

    Args:
        cwd [str | Path]: Repository root.
        codex_home [str | Path | None]: Optional Codex home used for capability detection.

    Returns:
        CodexAgentMaterializationStatus: Generated artifact status.
    """
    plan: CodexAgentMaterializationPlan = build_codex_agent_materialization_plan(
        cwd,
        codex_home=codex_home,
    )
    file_statuses: tuple[CodexAgentMaterializationFileStatus, ...] = tuple(
        _file_status(planned_file) for planned_file in plan.files
    )
    up_to_date: bool = bool(plan.supported) and all(
        file_status.matches for file_status in file_statuses
    )
    status = CodexAgentMaterializationStatus(
        up_to_date=up_to_date,
        supported=plan.supported,
        files=file_statuses,
        warning_count=len(plan.warnings),
        warnings=plan.warnings,
    )
    return status
