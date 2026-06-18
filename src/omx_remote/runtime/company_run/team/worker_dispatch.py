"""Build complete company-run Team worker dispatch packets."""

from omx_remote.schemas.company_run.company_run_governance_schemas import (
    CompanyRunWorkerDispatchPayload,
    CompanyRunWorkerDispatchRecord,
)
from omx_remote.shared.omx_enums.agent_enums import AgentEffort

_BASE_WORKER_OWNERSHIP_BOUNDARIES: tuple[str, ...] = (
    "surface-or-user-facing slice",
    "runtime-or-core slice",
    "tests-and-qa slice",
    "integration-and-conflict-resolution slice",
    "documentation-and-release-evidence slice",
    "security-hardening slice",
)

_BASE_WORKER_REASONING_POLICIES: tuple[tuple[AgentEffort, str], ...] = (
    (
        AgentEffort.MEDIUM,
        "Medium reasoning is enough for bounded user-facing and documentation work.",
    ),
    (
        AgentEffort.HIGH,
        "High reasoning is required for runtime/core contracts and data plumbing.",
    ),
    (
        AgentEffort.XHIGH,
        "Xhigh reasoning is required for QA, security, architecture, and blocker analysis.",
    ),
    (
        AgentEffort.XHIGH,
        "Xhigh reasoning is required for integration conflicts and release-readiness gates.",
    ),
    (
        AgentEffort.HIGH,
        "High reasoning is required for release evidence that must not overclaim readiness.",
    ),
    (
        AgentEffort.XHIGH,
        "Xhigh reasoning is required for security-hardening and high-stakes risk review.",
    ),
)

_EXTENSION_WORKER_REASONING_POLICY: tuple[AgentEffort, str] = (
    AgentEffort.HIGH,
    "High reasoning is the default for extension lanes until the CEO assigns a narrower scope.",
)

WORKER_BOUNDARY_SUBAGENT_RULE = (
    "Use scoped Codex subagents only for files, artifacts, and verification inside "
    "this worker ownership boundary; do not assign subagents to inspect, edit, or "
    "verify peer worker lanes unless the CEO/integration steward explicitly "
    "reassigns that boundary."
)


def worker_reasoning_effort(worker_index: int) -> AgentEffort:
    """Return the recommended reasoning effort for one worker lane.

    Args:
        worker_index [int]: One-based Team worker index.

    Returns:
        AgentEffort: Recommended Codex reasoning effort.
    """
    effort, _rationale = _worker_reasoning_policy(worker_index=worker_index)
    return effort


def worker_reasoning_rationale(worker_index: int) -> str:
    """Return the reasoning-effort rationale for one worker lane.

    Args:
        worker_index [int]: One-based Team worker index.

    Returns:
        str: Human-readable assignment rationale.
    """
    _effort, rationale = _worker_reasoning_policy(worker_index=worker_index)
    return rationale


def _worker_reasoning_policy(worker_index: int) -> tuple[AgentEffort, str]:
    """Return reasoning policy for one company-run Team worker.

    Args:
        worker_index [int]: One-based Team worker index.

    Returns:
        tuple[AgentEffort, str]: Effort and rationale.
    """
    if worker_index < 1:
        raise ValueError("company-run worker indexes are one-based")
    policy_index = worker_index - 1
    if policy_index < len(_BASE_WORKER_REASONING_POLICIES):
        policy = _BASE_WORKER_REASONING_POLICIES[policy_index]
        return policy
    return _EXTENSION_WORKER_REASONING_POLICY


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
        boundary = (
            f"worker-{worker_index} ownership lane: "
            f"{_BASE_WORKER_OWNERSHIP_BOUNDARIES[base_index]}"
        )
        return boundary
    extension_number = worker_index - len(_BASE_WORKER_OWNERSHIP_BOUNDARIES)
    boundary = (
        f"worker-{worker_index} ownership lane: extension slice "
        f"{extension_number}: scoped implementation, review, or integration "
        "support assigned by the CEO/integration steward"
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
    if not allowed_subagents:
        raise ValueError(
            "company-run worker dispatch requires at least one scoped Codex subagent"
        )
    if subagent_rule != WORKER_BOUNDARY_SUBAGENT_RULE:
        raise ValueError(
            "company-run worker dispatch requires the scoped Codex subagent boundary rule"
        )
    worker_packets = tuple(
        CompanyRunWorkerDispatchRecord(
            worker=f"worker-{worker_index}",
            objective=objective,
            ownership_boundary=worker_ownership_boundary(worker_index=worker_index),
            reasoning_effort=worker_reasoning_effort(worker_index=worker_index),
            reasoning_rationale=worker_reasoning_rationale(worker_index=worker_index),
            allowed_subagents=allowed_subagents,
            subagent_rule=subagent_rule,
        )
        for worker_index in range(1, worker_count + 1)
    )
    boundaries = tuple(packet.ownership_boundary for packet in worker_packets)
    if len(set(boundaries)) != len(boundaries):
        raise ValueError(
            "company-run worker dispatch requires separate ownership lanes"
        )
    dispatch_payload = CompanyRunWorkerDispatchPayload(
        workers=worker_packets,
        blocked_reasons=(),
    )
    return dispatch_payload
