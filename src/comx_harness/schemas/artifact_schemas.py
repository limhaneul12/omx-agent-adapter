from comx_harness.schemas.common_schemas import (
    NonEmptyString,
    Sha256Digest,
    StrictModel,
)
from comx_harness.shared.harness_enums.provider_enums import ProviderId
from pydantic import Field


class VerifiedArtifact(StrictModel):
    kind: NonEmptyString
    path: NonEmptyString
    required: bool
    exists: bool
    size_bytes: int = Field(ge=0)
    sha256: Sha256Digest | None = None
    source_run_id: NonEmptyString
    source_provider: ProviderId


class ArtifactReport(StrictModel):
    run_id: NonEmptyString
    artifacts: tuple[VerifiedArtifact, ...]
