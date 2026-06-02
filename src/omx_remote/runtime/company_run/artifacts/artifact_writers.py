from hashlib import sha256
from pathlib import Path

import orjson
from pydantic import BaseModel

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.artifacts.redacted_command_artifact_writer import (
    write_redacted_json_artifact,
)
from omx_remote.runtime.commands.rendering.command_output_redaction import redact_text
from omx_remote.schemas.company_run_schemas import (
    CompanyRunArtifactIndex,
    CompanyRunArtifactRecord,
    CompanyRunState,
)
from omx_remote.shared.omx_enums.company_run_enums import CompanyRunArtifactKind
from omx_remote.shared.utils.json_model_dump import model_json_value


def company_run_root(paths: ActualRunPaths) -> Path:
    """Return the run-local company-run root directory.

    Args:
        paths [ActualRunPaths]: Actual run paths.

    Returns:
        Path: Company-run artifact root.
    """
    root = paths.run_dir / "company-run"
    return root


def ensure_company_run_tree(root: Path) -> None:
    """Create the company-run artifact directory tree.

    Args:
        root [Path]: Company-run artifact root.
    """
    for relative in (
        "context",
        "discovery",
        "decisions",
        "research",
        "votes",
        "prd",
        "executive",
        "implementation",
        "team",
        "review",
        "release",
        "memory",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def write_company_markdown(path: Path, text: str) -> None:
    """Write redacted Markdown text to a company-run artifact.

    Args:
        path [Path]: Artifact path.
        text [str]: Markdown content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact_text(text), encoding="utf-8")


def write_company_json(path: Path, payload: object) -> None:
    """Write a JSON artifact using the repository redaction writer.

    Args:
        path [Path]: Artifact path.
        payload [object]: JSON-compatible payload.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    json_payload = model_json_value(payload) if isinstance(payload, BaseModel) else payload
    write_redacted_json_artifact(path, json_payload)


def append_phase_log(root: Path, entry: object) -> None:
    """Append one company-run phase ledger entry as redacted JSONL.

    Args:
        root [Path]: Company-run artifact root.
        entry [object]: JSON-compatible phase payload.
    """
    log_path = root / "phase-log.jsonl"
    json_entry = model_json_value(entry) if isinstance(entry, BaseModel) else entry
    encoded = orjson.dumps(json_entry).decode()
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(redact_text(encoded))
        log_file.write("\n")


def _file_sha256(path: Path) -> str | None:
    """Return SHA-256 for regular file artifacts.

    Args:
        path [Path]: Candidate artifact path.

    Returns:
        str | None: SHA-256 hex digest when path is a file.
    """
    if not path.is_file():
        missing_hash: None = None
        return missing_hash
    digest = sha256(path.read_bytes()).hexdigest()
    return digest


def artifact_record(
    kind: CompanyRunArtifactKind, path: Path
) -> CompanyRunArtifactRecord:
    """Build an artifact record for one company-run path.

    Args:
        kind [CompanyRunArtifactKind]: Artifact kind.
        path [Path]: Artifact path.

    Returns:
        CompanyRunArtifactRecord: Indexed artifact record.
    """
    exists = path.exists()
    size = path.stat().st_size if path.is_file() else 0
    record = CompanyRunArtifactRecord(
        kind=kind,
        path=str(path),
        exists=exists,
        size_bytes=size,
        sha256=_file_sha256(path),
    )
    return record


def write_company_state(root: Path, state: CompanyRunState) -> Path:
    """Persist the current company-run state snapshot.

    Args:
        root [Path]: Company-run artifact root.
        state [CompanyRunState]: State snapshot.

    Returns:
        Path: State artifact path.
    """
    state_path = root / "state.json"
    write_company_json(state_path, state)
    return state_path


def write_artifact_index(
    root: Path,
    run_id: str,
    records: tuple[CompanyRunArtifactRecord, ...],
) -> Path:
    """Persist a public company-run artifact index.

    Args:
        root [Path]: Company-run artifact root.
        run_id [str]: Actual run id.
        records [tuple[CompanyRunArtifactRecord, ...]]: Artifact records.

    Returns:
        Path: Artifact index path.
    """
    index = CompanyRunArtifactIndex(
        run_id=run_id,
        root_path=str(root),
        artifact_paths=tuple(record.path for record in records),
        artifacts=records,
    )
    index_path = root / "artifact-index.json"
    write_company_json(index_path, index)
    return index_path
