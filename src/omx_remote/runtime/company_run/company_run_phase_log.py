from pathlib import Path

from omx_remote.runtime.company_run.company_run_artifacts import append_phase_log
from omx_remote.schemas.company_run_schemas import (
    CompanyRunPhaseRecord,
    CompanyRunVoteRecord,
)
from omx_remote.shared.omx_enums.company_run_enums import (
    CompanyRunPhase,
    CompanyRunPhaseStatus,
)
from omx_remote.shared.utils.runtime_identity import utcnow_text


def append_company_run_phase(
    phase_records: list[CompanyRunPhaseRecord],
    phase: CompanyRunPhase,
    summary: str,
    artifacts: tuple,
    votes: tuple[CompanyRunVoteRecord, ...] = (),
    status: CompanyRunPhaseStatus = CompanyRunPhaseStatus.COMPLETE,
    blocked_reasons: tuple[str, ...] = (),
) -> None:
    """Append one company-run phase record and persist it to phase-log.jsonl.

    Args:
        phase_records [list[CompanyRunPhaseRecord]]: Mutable run phase log.
        phase [CompanyRunPhase]: Phase identifier being recorded.
        summary [str]: Human-readable phase outcome.
        artifacts [tuple]: Artifact records produced by the phase.
        votes [tuple[CompanyRunVoteRecord, ...]]: Vote records for the phase.
        status [CompanyRunPhaseStatus]: Phase status to persist.
        blocked_reasons [tuple[str, ...]]: Blockers attached to this phase.
    """
    timestamp = utcnow_text()
    record = CompanyRunPhaseRecord(
        phase=phase,
        status=status,
        summary=summary,
        started_at=timestamp,
        finished_at=timestamp,
        artifacts=artifacts,
        votes=votes,
        blocked_reasons=blocked_reasons,
    )
    phase_records.append(record)
    first_artifact = artifacts[0]
    company_root = Path(first_artifact.path)
    while company_root.name != "company-run" and company_root.parent != company_root:
        company_root = company_root.parent
    append_phase_log(company_root, record)
