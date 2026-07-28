from pathlib import Path

import pytest
from comx_harness.ade.artifact_content import ArtifactContentService
from comx_harness.schemas.artifact_schemas import ArtifactReport, VerifiedArtifact
from comx_harness.shared.harness_enums.provider_enums import ProviderId


def _report(path: Path, *, exists: bool = True) -> ArtifactReport:
    return ArtifactReport(
        run_id="run-1",
        artifacts=(
            VerifiedArtifact(
                kind="result",
                path=str(path),
                required=True,
                exists=exists,
                size_bytes=path.stat().st_size if path.exists() else 0,
                sha256=None,
                source_run_id="run-1",
                source_provider=ProviderId.CODEX,
            ),
        ),
    )


def test_reads_reported_utf8_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "result.md"
    artifact.write_text("verified result", encoding="utf-8")

    projection = ArtifactContentService().read(_report(artifact), str(artifact))

    assert projection.state == "available"
    assert projection.text == "verified result"


def test_rejects_unreported_path(tmp_path: Path) -> None:
    artifact = tmp_path / "result.md"
    artifact.write_text("verified result", encoding="utf-8")

    with pytest.raises(ValueError, match="not reported"):
        ArtifactContentService().read(_report(artifact), str(tmp_path / "other.md"))


def test_reports_display_limit_without_partial_content(tmp_path: Path) -> None:
    artifact = tmp_path / "large.log"
    artifact.write_text("12345", encoding="utf-8")

    projection = ArtifactContentService(maximum_bytes=4).read(
        _report(artifact),
        str(artifact),
    )

    assert projection.state == "too_large"
    assert projection.text is None
