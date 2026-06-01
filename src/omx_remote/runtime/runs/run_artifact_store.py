from pathlib import Path
from typing import Final

RUNS_ROOT: Final[str] = ".comx-agent/runs"


class RunArtifactPathError(ValueError):
    """Raised when a run artifact path would escape the run root."""


def _sanitize_run_component(value: str) -> str:
    """Sanitize one run id component.

    Args:
        value [str]: Raw component value.

    Returns:
        str: Filesystem-safe component.
    """
    characters: list[str] = []
    for character in value:
        if character.isalnum() or character in {"-", "_"}:
            characters.append(character)
        elif character in {":", "/", "\\", " ", "."}:
            characters.append("-")
    sanitized_value: str = "".join(characters).strip("-")
    if not sanitized_value:
        raise RunArtifactPathError("run id component normalized to empty text")
    return sanitized_value


def build_run_id(timestamp: str, command_id: str) -> str:
    """Build a deterministic run id from a timestamp and command id.

    Args:
        timestamp [str]: Timestamp prefix.
        command_id [str]: Command id or qualified command id.

    Returns:
        str: Safe run id.
    """
    timestamp_component: str = _sanitize_run_component(timestamp)
    command_component: str = _sanitize_run_component(command_id)
    run_id: str = f"{timestamp_component}-{command_component}"
    return run_id


def resolve_runs_root(cwd: str | Path) -> Path:
    """Resolve the run artifact root for a repository.

    Args:
        cwd [str | Path]: Repository root.

    Returns:
        Path: `.comx-agent/runs` path under the repository.
    """
    root_path: Path = Path(cwd).resolve()
    runs_root: Path = root_path / RUNS_ROOT
    return runs_root


def _validate_run_id(run_id: str) -> None:
    """Validate that a run id is one safe path segment.

    Args:
        run_id [str]: Run id to validate.
    """
    if run_id != _sanitize_run_component(run_id):
        raise RunArtifactPathError(f"unsafe run id: {run_id}")


def resolve_run_dir(cwd: str | Path, run_id: str) -> Path:
    """Resolve one run directory and reject traversal.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Run id path segment.

    Returns:
        Path: Run directory path.
    """
    _validate_run_id(run_id)
    runs_root: Path = resolve_runs_root(cwd)
    run_dir: Path = (runs_root / run_id).resolve()
    if runs_root not in run_dir.parents:
        raise RunArtifactPathError(f"unsafe run id: {run_id}")
    return run_dir


def ensure_run_dir(cwd: str | Path, run_id: str) -> Path:
    """Create and return one run directory.

    Args:
        cwd [str | Path]: Repository root.
        run_id [str]: Safe run id.

    Returns:
        Path: Created run directory.
    """
    run_dir: Path = resolve_run_dir(cwd, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def allocate_unique_run_dir(
    cwd: str | Path,
    timestamp: str,
    command_id: str,
) -> tuple[str, Path]:
    """Atomically allocate a non-overwriting run directory.

    Args:
        cwd [str | Path]: Repository root.
        timestamp [str]: Timestamp prefix.
        command_id [str]: Command id or qualified command id.

    Returns:
        tuple[str, Path]: Unique run id and created run directory.
    """
    base_run_id: str = build_run_id(timestamp, command_id)
    candidate_run_id: str = base_run_id
    suffix = 2
    while True:
        run_dir: Path = resolve_run_dir(cwd, candidate_run_id)
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return candidate_run_id, run_dir
        except FileExistsError:
            candidate_run_id = f"{base_run_id}-{suffix:02d}"
            suffix += 1
