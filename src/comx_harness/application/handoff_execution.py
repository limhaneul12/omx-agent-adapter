from pathlib import Path

from comx_harness.run_evidence import collect_run_artifacts
from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.handoff_schemas import HandoffRequest
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.shared.exceptions.harness_exceptions import (
    ArtifactNotFoundError,
    UnsupportedOperationError,
)
from comx_harness.storage.harness_storage import HarnessStorage


def select_handoff_artifact(
    *,
    storage: HarnessStorage,
    source_record: RunRecord,
    artifact_kind: str,
) -> VerifiedArtifact:
    artifacts = collect_run_artifacts(
        storage,
        source_record,
        include_declared=True,
    )
    artifact = next(
        (item for item in artifacts if item.kind == artifact_kind),
        None,
    )
    if artifact is None or not artifact.exists or artifact.size_bytes == 0:
        raise ArtifactNotFoundError(
            f"verified artifact {artifact_kind!r} is unavailable"
        )
    return artifact


def read_handoff_text(path: str) -> str:
    try:
        source_text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise UnsupportedOperationError(
            "cross-runtime handoff currently supports UTF-8 text artifacts only"
        ) from error
    return source_text


def build_handoff_objective(
    *,
    request: HandoffRequest,
    source_record: RunRecord,
    source_text: str,
    digest: str | None,
) -> str:
    objective = (
        f"{request.objective}\n\n"
        "The following verified artifact was produced by another runtime. "
        "Use it as input, preserve its provenance, and independently verify "
        "any claim before acting.\n\n"
        f"origin_run_id: {source_record.run_id}\n"
        f"source_provider: {source_record.provider}\n"
        f"artifact_sha256: {digest}\n\n"
        "--- artifact ---\n"
        f"{source_text}"
    )
    return objective
