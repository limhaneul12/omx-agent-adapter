from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_READINESS_DOC = REPO_ROOT / "docs" / "future-runtime-readiness.md"
SOURCE_PATH_PATTERN = re.compile(r"`(src/[A-Za-z0-9_./-]+\.py)`")


def test_future_runtime_readiness_references_current_source_paths() -> None:
    source_paths = SOURCE_PATH_PATTERN.findall(RUNTIME_READINESS_DOC.read_text())

    assert source_paths, "expected runtime readiness doc to reference source paths"

    missing_paths = [path for path in source_paths if not (REPO_ROOT / path).exists()]

    assert missing_paths == []
