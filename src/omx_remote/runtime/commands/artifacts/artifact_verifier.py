from hashlib import sha256
from pathlib import Path

from omx_remote.schemas.commands.command_execution_schemas import CommandArtifactCheck


def _file_sha256(path: Path) -> str | None:
    """Return a file hash for regular files.

    Args:
        path: See function signature.

    Returns:
        See function return annotation."""
    if not path.is_file():
        no_hash: None = None
        return no_hash
    digest: str = sha256(path.read_bytes()).hexdigest()
    return digest


def _artifact_size(path: Path) -> int:
    """Return a stable size for files and directories.

    Args:
        path: See function signature.

    Returns:
        See function return annotation."""
    if not path.exists():
        missing_size = 0
        return missing_size
    if path.is_file():
        file_size: int = path.stat().st_size
        return file_size
    directory_size = 0
    return directory_size


class ArtifactVerifier:
    """Verify expected command artifacts and collect hash evidence."""

    def check(self, path: str | Path, required: bool = True) -> CommandArtifactCheck:
        """Check one artifact path.

        Args:
            path: See function signature.
            required: See function signature.

        Returns:
            See function return annotation."""
        artifact_path: Path = Path(path)
        exists: bool = artifact_path.exists()
        note: str | None = None
        if exists and artifact_path.is_dir():
            note = "artifact path is a directory"
        check = CommandArtifactCheck(
            path=str(artifact_path),
            exists=exists,
            size_bytes=_artifact_size(artifact_path),
            sha256=_file_sha256(artifact_path),
            required=required,
            note=note,
        )
        return check

    def check_many(
        self,
        paths: tuple[str | Path, ...],
        required: bool = True,
    ) -> tuple[CommandArtifactCheck, ...]:
        """Check multiple artifact paths.

        Args:
            paths: See function signature.
            required: See function signature.

        Returns:
            See function return annotation."""
        checks: tuple[CommandArtifactCheck, ...] = tuple(
            self.check(path, required=required) for path in paths
        )
        return checks
