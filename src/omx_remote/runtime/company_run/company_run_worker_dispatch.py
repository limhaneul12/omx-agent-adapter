"""Build complete company-run Team worker dispatch packets."""

from omx_remote.schemas.company_run_schemas import (
    CompanyRunWorkerDispatchPayload,
    CompanyRunWorkerDispatchRecord,
)

_BASE_WORKER_OWNERSHIP_BOUNDARIES: tuple[str, ...] = (
    "surface-or-user-facing slice",
    "runtime-or-core slice",
    "tests-and-qa slice",
    "integration-and-conflict-resolution slice",
    "documentation-and-release-evidence slice",
    "security-hardening slice",
)


def worker_ownership_boundary(worker_index: int) -> str:
    """Return one stable ownership boundary for a company-run Team worker.

    Args:
        worker_index [int]: One-based Team worker index.

    Returns:
        str: Worker ownership boundary text.
    """
    if worker_index < 1:
        raise ValueError("company-run worker indexes are one-based")
    base_index = worker_index - 1
    if base_index < len(_BASE_WORKER_OWNERSHIP_BOUNDARIES):
        boundary = _BASE_WORKER_OWNERSHIP_BOUNDARIES[base_index]
        return boundary
    extension_number = worker_index - len(_BASE_WORKER_OWNERSHIP_BOUNDARIES)
    boundary = (
        f"extension slice {extension_number}: scoped implementation, review, "
        "or integration support assigned by the CEO/integration steward"
    )
    return boundary


def build_worker_dispatch_payload(
    objective: str,
    worker_count: int,
    allowed_subagents: tuple[str, ...],
    subagent_rule: str,
) -> CompanyRunWorkerDispatchPayload:
    """Build one dispatch packet for every requested Team worker.

    Args:
        objective [str]: Company-run objective.
        worker_count [int]: Requested Team worker count.
        allowed_subagents [tuple[str, ...]]: Subagents each worker may use inside its ownership boundary.
        subagent_rule [str]: Rule text to attach to every worker packet.

    Returns:
        CompanyRunWorkerDispatchPayload: Complete dispatch payload.
    """
    if worker_count < 1:
        raise ValueError("company-run worker dispatch requires at least one worker")
    worker_packets = tuple(
        CompanyRunWorkerDispatchRecord(
            worker=f"worker-{worker_index}",
            objective=objective,
            ownership_boundary=worker_ownership_boundary(worker_index=worker_index),
            allowed_subagents=allowed_subagents,
            subagent_rule=subagent_rule,
        )
        for worker_index in range(1, worker_count + 1)
    )
    dispatch_payload = CompanyRunWorkerDispatchPayload(
        workers=worker_packets,
        blocked_reasons=(),
    )
    return dispatch_payload
