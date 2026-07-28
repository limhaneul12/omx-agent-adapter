from __future__ import annotations

from pathlib import Path

from comx_harness.schemas.ade_inspection_schemas import (
    ArtifactContentProjection,
    ArtifactContentState,
)
from comx_harness.schemas.artifact_schemas import ArtifactReport, VerifiedArtifact


class ArtifactContentService:
    """Read bounded UTF-8 content only from core-reported artifact paths."""

    def __init__(self, *, maximum_bytes: int = 512_000) -> None:
        if maximum_bytes < 1:
            raise ValueError("maximum_bytes must be positive")
        self._maximum_bytes = maximum_bytes

    def read(
        self,
        report: ArtifactReport,
        artifact_path: str,
    ) -> ArtifactContentProjection:
        """Read one artifact after revalidating its report entry.

        Args:
            report [ArtifactReport]: Core artifact report for the selected Run.
            artifact_path [str]: Exact path selected from that report.

        Returns:
            ArtifactContentProjection: Bounded text or an honest unavailable state.
        """
        artifact = self._reported_artifact(report, artifact_path)
        if artifact is None:
            raise ValueError("artifact path was not reported by the execution core")
        path = Path(artifact.path)
        if not artifact.exists or not path.is_file():
            return self._projection(
                report=report,
                artifact=artifact,
                state="missing",
                text=None,
                message="artifact is missing from the filesystem",
            )
        try:
            payload = path.read_bytes()
        except OSError as error:
            return self._projection(
                report=report,
                artifact=artifact,
                state="error",
                text=None,
                message=str(error),
            )
        if len(payload) > self._maximum_bytes:
            return self._projection(
                report=report,
                artifact=artifact,
                state="too_large",
                text=None,
                message=f"artifact exceeds {self._maximum_bytes} byte display limit",
            )
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            return self._projection(
                report=report,
                artifact=artifact,
                state="binary",
                text=None,
                message="artifact is not valid UTF-8 text",
            )
        return self._projection(
            report=report,
            artifact=artifact,
            state="available",
            text=text,
            message=None,
        )

    @staticmethod
    def _reported_artifact(
        report: ArtifactReport,
        artifact_path: str,
    ) -> VerifiedArtifact | None:
        return next(
            (
                artifact
                for artifact in report.artifacts
                if artifact.path == artifact_path
            ),
            None,
        )

    @staticmethod
    def _projection(
        *,
        report: ArtifactReport,
        artifact: VerifiedArtifact,
        state: ArtifactContentState,
        text: str | None,
        message: str | None,
    ) -> ArtifactContentProjection:
        return ArtifactContentProjection(
            run_id=report.run_id,
            kind=artifact.kind,
            path=artifact.path,
            state=state,
            size_bytes=artifact.size_bytes,
            text=text,
            message=message,
        )
