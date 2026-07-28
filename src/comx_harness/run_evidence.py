from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from comx_harness.schemas.artifact_schemas import VerifiedArtifact
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.storage.harness_storage import HarnessStorage


def collect_run_artifacts(
    storage: HarnessStorage,
    record: RunRecord,
    *,
    include_declared: bool,
) -> tuple[VerifiedArtifact, ...]:
    """Verify harness-owned and controller-declared artifacts for one run."""
    plan = storage.runs.read_plan(record.run_id)
    candidates: list[tuple[str, Path, bool]] = [
        ("result", Path(plan.result_path), True),
        ("stdout", Path(plan.stdout_path), False),
        ("stderr", Path(plan.stderr_path), False),
        ("events", Path(plan.events_path), False),
        ("plan", Path(record.plan_path), True),
    ]
    if include_declared:
        for artifact_text in plan.request.expected_artifacts:
            artifact_path = Path(artifact_text)
            if not artifact_path.is_absolute():
                artifact_path = Path(plan.cwd) / artifact_path
            candidates.append(("expected", artifact_path, True))

    artifacts: list[VerifiedArtifact] = []
    seen_paths: set[str] = set()
    for kind, path, required in candidates:
        resolved_path = path.resolve()
        path_text = str(resolved_path)
        if path_text in seen_paths:
            continue
        seen_paths.add(path_text)
        exists = resolved_path.exists()
        is_file = exists and resolved_path.is_file()
        size_bytes = resolved_path.stat().st_size if is_file else 0
        digest = sha256(resolved_path.read_bytes()).hexdigest() if is_file else None
        artifacts.append(
            VerifiedArtifact(
                kind=kind,
                path=path_text,
                required=required,
                exists=exists,
                size_bytes=size_bytes,
                sha256=digest,
                source_run_id=record.run_id,
                source_provider=record.provider,
            )
        )
    verified_artifacts = tuple(artifacts)
    return verified_artifacts


def required_artifact_failures(
    artifacts: tuple[VerifiedArtifact, ...],
) -> tuple[VerifiedArtifact, ...]:
    """Return required artifacts that are missing or empty."""
    failures = tuple(
        artifact
        for artifact in artifacts
        if artifact.required and (not artifact.exists or artifact.size_bytes == 0)
    )
    return failures
