from pathlib import Path

ALEXANDRIA_VAULT_ROOT = Path("/Users/imhaneul/Desktop/Alexandria")
CODEX_SKILLS_ROOT = Path.home() / ".codex" / "skills"


def _is_under(path: Path, root: Path) -> bool:
    """Return whether path is inside root after resolution.

    Args:
        path: See function signature.
        root: See function signature.

    Returns:
        See function return annotation."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def validate_materialized_artifact_path(path: Path, cwd: str | Path) -> Path:
    """Validate and resolve a path before the executor writes a handoff artifact.

    Args:
        path: See function signature.
        cwd: See function signature.

    Returns:
        See function return annotation."""
    cwd_path = Path(cwd).resolve()
    candidate_path: Path = path if path.is_absolute() else cwd_path / path
    resolved_path: Path = candidate_path.resolve()
    if _is_under(resolved_path, cwd_path):
        return resolved_path
    if _is_under(resolved_path, ALEXANDRIA_VAULT_ROOT):
        return resolved_path
    if _is_under(resolved_path, CODEX_SKILLS_ROOT):
        return resolved_path
    raise ValueError(
        "Refusing to materialize artifact outside the repository, Alexandria vault, or Codex skills root: "
        f"{resolved_path}"
    )
