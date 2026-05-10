from omx_remote.adapter_types.type_contract.teamwork_contract_type import (
    TEAM_COMPLETION_EVENT_TYPES,
    TEAM_DISPATCH_EVENT_TYPES,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitStatusSourceState,
    CockpitTeamProofLayerName,
    CockpitTeamProofLayerObservation,
    CockpitTeamWorkerObservation,
)
from omx_remote.schemas.teamwork.api_snapshot_schemas import (
    TeamApiListTasksSnapshot,
    TeamApiReadEventsSnapshot,
)
from omx_remote.shared.omx_enums.teamwork_enums import TeamEventType
from omx_remote.teamwork.team_admin_aggregation import (
    COMPLETED_TASK_STATES,
    normalize_state_token,
)


def _build_team_proof_layers(
    tasks_snapshot: TeamApiListTasksSnapshot | None,
    events_snapshot: TeamApiReadEventsSnapshot | None,
    worker_names: tuple[str, ...],
    worker_statuses: tuple[CockpitTeamWorkerObservation, ...],
    warnings: tuple[str, ...],
) -> tuple[CockpitTeamProofLayerObservation, ...]:
    """Classify Team evidence into read-only launch/status proof layers.

    Args:
        tasks_snapshot [TeamApiListTasksSnapshot | None]: Optional task evidence.
        events_snapshot [TeamApiReadEventsSnapshot | None]: Optional event evidence.
        worker_names [tuple[str, ...]]: Workers inferred from status/task/event evidence.
        worker_statuses [tuple[CockpitTeamWorkerObservation, ...]]: Read worker states.
        warnings [tuple[str, ...]]: Read warnings collected while probing Team surfaces.

    Returns:
        tuple[CockpitTeamProofLayerObservation, ...]: Ordered proof-layer observations.
    """
    proof_layers: tuple[CockpitTeamProofLayerObservation, ...] = (
        _build_assignment_import_proof_layer(tasks_snapshot),
        _build_worker_readiness_proof_layer(worker_names, worker_statuses, warnings),
        _build_dispatch_proof_layer(events_snapshot),
        _build_completion_proof_layer(tasks_snapshot, events_snapshot),
    )
    return proof_layers


def _build_assignment_import_proof_layer(
    tasks_snapshot: TeamApiListTasksSnapshot | None,
) -> CockpitTeamProofLayerObservation:
    """Classify Team task owner evidence as assignment/import proof.

    Args:
        tasks_snapshot [TeamApiListTasksSnapshot | None]: Optional task evidence.

    Returns:
        CockpitTeamProofLayerObservation: Assignment/import proof classification.
    """
    if tasks_snapshot is None:
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.ASSIGNMENT_IMPORT,
            state=CockpitStatusSourceState.FAILED,
            detail="Team task evidence could not be read; assignment/import proof is unavailable.",
            source_names=("team_api.list_tasks",),
        )

    owner_count: int = sum(1 for task_snapshot in tasks_snapshot.tasks if task_snapshot.owner)
    if owner_count > 0:
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.ASSIGNMENT_IMPORT,
            state=CockpitStatusSourceState.OBSERVED,
            detail=f"Observed {owner_count} Team task owner assignment(s).",
            source_names=("team_api.list_tasks",),
        )

    return CockpitTeamProofLayerObservation(
        layer=CockpitTeamProofLayerName.ASSIGNMENT_IMPORT,
        state=CockpitStatusSourceState.MISSING,
        detail="Team tasks were read but no task owner assignment evidence was found.",
        source_names=("team_api.list_tasks",),
    )


def _build_worker_readiness_proof_layer(
    worker_names: tuple[str, ...],
    worker_statuses: tuple[CockpitTeamWorkerObservation, ...],
    warnings: tuple[str, ...],
) -> CockpitTeamProofLayerObservation:
    """Classify worker-status reads as worker readiness proof.

    Args:
        worker_names [tuple[str, ...]]: Workers inferred from Team evidence.
        worker_statuses [tuple[CockpitTeamWorkerObservation, ...]]: Read worker states.
        warnings [tuple[str, ...]]: Read warnings collected while probing Team surfaces.

    Returns:
        CockpitTeamProofLayerObservation: Worker readiness proof classification.
    """
    if worker_statuses:
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.WORKER_READINESS,
            state=CockpitStatusSourceState.OBSERVED,
            detail=f"Observed {len(worker_statuses)} Team worker status snapshot(s).",
            source_names=("team_api.read_worker_status",),
        )

    if worker_names and _has_warning_prefix(warnings, "team worker-status read failed"):
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.WORKER_READINESS,
            state=CockpitStatusSourceState.FAILED,
            detail="Team workers were inferred but worker status evidence could not be read.",
            source_names=("team_api.read_worker_status",),
        )

    return CockpitTeamProofLayerObservation(
        layer=CockpitTeamProofLayerName.WORKER_READINESS,
        state=CockpitStatusSourceState.MISSING,
        detail="No Team worker readiness evidence was found.",
        source_names=("team_api.read_worker_status",),
    )


def _build_dispatch_proof_layer(
    events_snapshot: TeamApiReadEventsSnapshot | None,
) -> CockpitTeamProofLayerObservation:
    """Classify Team events as dispatch proof.

    Args:
        events_snapshot [TeamApiReadEventsSnapshot | None]: Optional event evidence.

    Returns:
        CockpitTeamProofLayerObservation: Dispatch proof classification.
    """
    if events_snapshot is None:
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.DISPATCH,
            state=CockpitStatusSourceState.FAILED,
            detail="Team event evidence could not be read; dispatch proof is unavailable.",
            source_names=("team_api.read_events",),
        )

    dispatch_event_count: int = sum(
        1 for event_snapshot in events_snapshot.events if _is_dispatch_event(event_snapshot.type)
    )
    if dispatch_event_count > 0:
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.DISPATCH,
            state=CockpitStatusSourceState.OBSERVED,
            detail=f"Observed {dispatch_event_count} Team dispatch event(s).",
            source_names=("team_api.read_events",),
        )

    return CockpitTeamProofLayerObservation(
        layer=CockpitTeamProofLayerName.DISPATCH,
        state=CockpitStatusSourceState.MISSING,
        detail="Team events were read but no dispatch evidence was found.",
        source_names=("team_api.read_events",),
    )


def _build_completion_proof_layer(
    tasks_snapshot: TeamApiListTasksSnapshot | None,
    events_snapshot: TeamApiReadEventsSnapshot | None,
) -> CockpitTeamProofLayerObservation:
    """Classify task/event evidence as Team completion proof.

    Args:
        tasks_snapshot [TeamApiListTasksSnapshot | None]: Optional task evidence.
        events_snapshot [TeamApiReadEventsSnapshot | None]: Optional event evidence.

    Returns:
        CockpitTeamProofLayerObservation: Completion proof classification.
    """
    source_names: tuple[str, ...] = _completion_source_names()
    completed_task_count: int = 0
    if tasks_snapshot is not None:
        completed_task_count = sum(
            1 for task_snapshot in tasks_snapshot.tasks if _is_completed_status(task_snapshot.status)
        )
    completed_event_count: int = 0
    if events_snapshot is not None:
        completed_event_count = sum(
            1 for event_snapshot in events_snapshot.events if _is_completion_event(event_snapshot.type)
        )

    if completed_task_count > 0 or completed_event_count > 0:
        evidence_count: int = completed_task_count + completed_event_count
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.COMPLETION,
            state=CockpitStatusSourceState.OBSERVED,
            detail=f"Observed {evidence_count} Team completion evidence item(s).",
            source_names=source_names,
        )

    if tasks_snapshot is None or events_snapshot is None:
        return CockpitTeamProofLayerObservation(
            layer=CockpitTeamProofLayerName.COMPLETION,
            state=CockpitStatusSourceState.FAILED,
            detail="Team task or event evidence could not be read; completion proof is unavailable.",
            source_names=source_names,
        )

    return CockpitTeamProofLayerObservation(
        layer=CockpitTeamProofLayerName.COMPLETION,
        state=CockpitStatusSourceState.MISSING,
        detail="Team tasks/events were read but no completion evidence was found.",
        source_names=source_names,
    )


def _completion_source_names() -> tuple[str, ...]:
    """Return source names consulted for completion classification.

    Returns:
        tuple[str, ...]: Completion classification source names.
    """
    return ("team_api.list_tasks", "team_api.read_events")


def _is_completed_status(status: str) -> bool:
    """Return whether a Team task status represents completion evidence.

    Args:
        status [str]: Team task status text.

    Returns:
        bool: True when the status represents completed work.
    """
    return normalize_state_token(status) in COMPLETED_TASK_STATES


def _is_completion_event(event_type: str) -> bool:
    """Return whether a Team event type represents completion evidence.

    Args:
        event_type [str]: Team event type text.

    Returns:
        bool: True when the event represents completed work.
    """
    normalized_event_type: TeamEventType | None = _normalize_team_event_type(event_type)
    is_completion_event: bool = normalized_event_type in TEAM_COMPLETION_EVENT_TYPES
    return is_completion_event


def _is_dispatch_event(event_type: str) -> bool:
    """Return whether a Team event type represents dispatch evidence.

    Args:
        event_type [str]: Team event type text.

    Returns:
        bool: True when the event represents dispatch evidence.
    """
    normalized_event_type: TeamEventType | None = _normalize_team_event_type(event_type)
    is_dispatch_event: bool = normalized_event_type in TEAM_DISPATCH_EVENT_TYPES
    return is_dispatch_event


def _normalize_team_event_type(event_type: str) -> TeamEventType | None:
    """Normalize raw Team event text into a known Team event type.

    Args:
        event_type [str]: Team event type text from the Team API.

    Returns:
        TeamEventType | None: Known Team event type, or None for unrecognized input.
    """
    normalized_event_text: str = event_type.lower()
    try:
        normalized_event_type: TeamEventType | None = TeamEventType(normalized_event_text)
    except ValueError:
        normalized_event_type = None
    return normalized_event_type


def _has_warning_prefix(warnings: tuple[str, ...], prefix: str) -> bool:
    """Return whether a collected Team warning starts with a prefix.

    Args:
        warnings [tuple[str, ...]]: Collected warning texts.
        prefix [str]: Warning prefix to match.

    Returns:
        bool: True when at least one warning starts with the prefix.
    """
    return any(warning.startswith(prefix) for warning in warnings)
