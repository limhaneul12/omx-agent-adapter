from omx_remote.schemas.cockpit.snapshot_schemas import CockpitTeamObservation
from omx_remote.schemas.teamwork.proof_layer_schemas import (
    TeamProofLayerName,
    TeamProofLayerState,
    TeamProofLayerSummary,
)
from omx_remote.teamwork.team_proof_layers import normalize_proof_state_token

STARTUP_ISSUE_WORKER_STATES: frozenset[str] = frozenset(
    {
        "ready_prompt_timeout",
        "startup_prompt_timeout",
        "startup_timeout",
        "worker_startup_timeout",
    }
)
COMPLETION_TEAM_STATUSES: frozenset[str] = frozenset(
    {"complete", "completed", "done", "success", "succeeded"}
)


def build_cockpit_team_observation_proof_layers(
    observation: CockpitTeamObservation,
) -> tuple[TeamProofLayerSummary, ...]:
    """Build best-effort proof layers from cockpit Team observations.

    Args:
        observation [CockpitTeamObservation]: Read-only Team evidence included in cockpit.

    Returns:
        tuple[TeamProofLayerSummary, ...]: Ordered proof-layer summaries.
    """
    worker_count: int = len(observation.worker_statuses)
    status_token: str = normalize_proof_state_token(observation.status)
    has_startup_issue: bool = any(
        normalize_proof_state_token(worker.state) in STARTUP_ISSUE_WORKER_STATES
        for worker in observation.worker_statuses
    )

    prd_layer = TeamProofLayerSummary(
        name=TeamProofLayerName.PRD_DAG_IMPORT,
        state=TeamProofLayerState.UNKNOWN,
        summary="Cockpit Team evidence does not include Ralph PRD/DAG import proof.",
        source_names=("omx_team_status",),
        blocking=False,
    )
    assignment_state: TeamProofLayerState = TeamProofLayerState.MISSING
    assignment_blocking: bool = True
    if worker_count or observation.task_count:
        assignment_state = TeamProofLayerState.PASSED
        assignment_blocking = False
    assignment_layer = TeamProofLayerSummary(
        name=TeamProofLayerName.ASSIGNMENT,
        state=assignment_state,
        summary=f"Observed {worker_count} worker status and {observation.task_count} task record.",
        source_names=("omx_team_api_list_tasks", "omx_team_api_read_worker_status"),
        blocking=assignment_blocking,
    )

    readiness_state: TeamProofLayerState = TeamProofLayerState.UNKNOWN
    readiness_summary: str = "Worker readiness has not been proven from cockpit evidence."
    readiness_blocking: bool = False
    if has_startup_issue:
        readiness_state = TeamProofLayerState.FAILED
        readiness_summary = "Worker readiness failed because startup timeout evidence is present."
        readiness_blocking = True
    elif worker_count:
        readiness_state = TeamProofLayerState.PARTIAL
        readiness_summary = f"Observed readiness state for {worker_count} worker."
        readiness_blocking = status_token == "active"
    worker_readiness_layer = TeamProofLayerSummary(
        name=TeamProofLayerName.WORKER_READINESS,
        state=readiness_state,
        summary=readiness_summary,
        source_names=("omx_team_api_read_worker_status",),
        blocking=readiness_blocking,
    )

    dispatch_state: TeamProofLayerState = TeamProofLayerState.MISSING
    dispatch_blocking: bool = True
    if observation.task_count or observation.event_count:
        dispatch_state = TeamProofLayerState.PARTIAL
        dispatch_blocking = status_token == "active"
    dispatch_layer = TeamProofLayerSummary(
        name=TeamProofLayerName.DISPATCH,
        state=dispatch_state,
        summary=(
            f"Observed {observation.task_count} task and "
            f"{observation.event_count} Team event record."
        ),
        source_names=("omx_team_api_list_tasks", "omx_team_api_read_events"),
        blocking=dispatch_blocking,
    )

    completion_state: TeamProofLayerState = TeamProofLayerState.MISSING
    completion_blocking: bool = status_token == "active"
    if status_token in COMPLETION_TEAM_STATUSES:
        completion_state = TeamProofLayerState.PASSED
        completion_blocking = False
    elif observation.task_count or observation.event_count:
        completion_state = TeamProofLayerState.PARTIAL
    completion_layer = TeamProofLayerSummary(
        name=TeamProofLayerName.COMPLETION,
        state=completion_state,
        summary=f"Team status is {observation.status}; merge readiness is not inferred by cockpit.",
        source_names=("omx_team_status", "omx_team_api_list_tasks", "omx_team_api_read_events"),
        blocking=completion_blocking,
    )

    layers: tuple[TeamProofLayerSummary, ...] = (
        prd_layer,
        assignment_layer,
        worker_readiness_layer,
        dispatch_layer,
        completion_layer,
    )
    return layers


def collect_blocking_team_proof_layer_source_names(
    observation: CockpitTeamObservation,
) -> tuple[str, ...]:
    """Collect source markers for blocking proof layers on a cockpit Team observation.

    Args:
        observation [CockpitTeamObservation]: Cockpit Team evidence.

    Returns:
        tuple[str, ...]: Ordered source names suitable for decision reasons.
    """
    source_names: list[str] = []
    seen_source_names: set[str] = set()
    for layer in observation.proof_layers:
        if not layer.blocking:
            continue
        layer_source_name: str = f"team_proof_layer:{layer.name}"
        for source_name in (layer_source_name, *layer.source_names):
            if source_name in seen_source_names:
                continue
            seen_source_names.add(source_name)
            source_names.append(source_name)

    result: tuple[str, ...] = tuple(source_names)
    return result
