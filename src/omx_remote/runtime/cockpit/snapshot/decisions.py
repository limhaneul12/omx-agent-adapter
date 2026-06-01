from omx_remote.runtime.cockpit.team_evidence.proof_layers import (
    collect_blocking_team_proof_layer_source_names,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitContradiction,
    CockpitDecisionReason,
    CockpitTeamObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime_status_schemas import ActiveRuntimeModes, RuntimeStatus
from omx_remote.shared.omx_enums.codex_goal_enums import CodexGoalHandoffState

_ACTIVE_TEAM_STATUSES: tuple[str, ...] = ("active",)


def _build_runtime_contradictions(
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
) -> tuple[CockpitContradiction, ...]:
    """Build contradictions between runtime status and active-mode surfaces.

    Args:
        runtime_status [RuntimeStatus]: Normalized `omx status` snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Normalized active mode list.

    Returns:
        tuple[CockpitContradiction, ...]: Detected runtime contradictions.
    """
    contradictions: list[CockpitContradiction] = []
    status_active_modes: set[str] = set(runtime_status.active_mode_names)
    listed_active_modes: set[str] = set(active_runtime_modes.active_modes)
    if listed_active_modes and (
        runtime_status.has_active_modes is False or not status_active_modes
    ):
        active_modes_text: str = ", ".join(active_runtime_modes.active_modes)
        contradictions.append(
            CockpitContradiction(
                category="runtime_activity_conflict",
                message=(
                    "omx status reports no parseable active modes, but omx state list-active "
                    f"reports active modes: {active_modes_text}"
                ),
            )
        )

    result: tuple[CockpitContradiction, ...] = tuple(contradictions)
    return result


def _runtime_status_has_uncertain_activity(runtime_status: RuntimeStatus) -> bool:
    """Return whether runtime activity is unknown enough to require inspection.

    Args:
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.

    Returns:
        bool: ``True`` when `omx status` did not produce a definitive activity signal.
    """
    has_uncertain_activity: bool = runtime_status.has_active_modes is None
    return has_uncertain_activity


def _derive_safe_to_mutate(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    team_observations: tuple[CockpitTeamObservation, ...],
) -> bool:
    """Derive whether cockpit observations are safe for mutation.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        bool: ``True`` only when no active runtime, active Team, or contradictions are visible.
    """
    has_active_runtime: bool = (
        bool(active_runtime_modes.active_modes)
        or runtime_status.has_active_modes is True
    )
    has_uncertain_runtime: bool = _runtime_status_has_uncertain_activity(runtime_status)
    has_active_team: bool = _team_observations_include_active_runtime(team_observations)
    safe_to_mutate: bool = (
        not contradictions
        and not has_active_runtime
        and not has_uncertain_runtime
        and not has_active_team
    )
    return safe_to_mutate


def _derive_recommended_next_action(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    goal_mirror_state: CodexGoalMirrorState | None,
    team_observations: tuple[CockpitTeamObservation, ...],
) -> str:
    """Derive one top-level next action from cockpit observations.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        str: Top-level recommended next action marker.
    """
    if contradictions:
        contradiction_action: str = "inspect_runtime_contradiction"
        return contradiction_action
    if active_runtime_modes.active_modes or runtime_status.has_active_modes is True:
        observe_action: str = "observe_active_runtime"
        return observe_action
    if _runtime_status_has_uncertain_activity(runtime_status):
        inspect_runtime_action: str = "inspect_runtime_status"
        return inspect_runtime_action
    if _team_observations_include_active_runtime(team_observations):
        inspect_team_action: str = "inspect_team_evidence"
        return inspect_team_action
    if (
        goal_mirror_state
        and goal_mirror_state.handoff_state == CodexGoalHandoffState.AWAITING_RALPH
    ):
        prepare_action: str = "prepare_ralph"
        return prepare_action

    default_action: str = "observe"
    return default_action


def _build_decision_reasons(
    contradictions: tuple[CockpitContradiction, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    goal_mirror_state: CodexGoalMirrorState | None,
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[CockpitDecisionReason, ...]:
    """Build evidence-backed explanations for top-level cockpit guidance.

    Args:
        contradictions [tuple[CockpitContradiction, ...]]: Cross-surface contradictions.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime mode list.
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror state.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[CockpitDecisionReason, ...]: Ordered reasons matching top-level cockpit guidance.
    """
    reasons: list[CockpitDecisionReason] = [
        CockpitDecisionReason(
            category="runtime_contradiction",
            detail=contradiction.message,
            recommended_next_action="inspect_runtime_contradiction",
            blocks_mutation=True,
            source_names=("runtime_status", "active_runtime_modes"),
        )
        for contradiction in contradictions
    ]

    if active_runtime_modes.active_modes:
        active_modes_text: str = ", ".join(active_runtime_modes.active_modes)
        reasons.append(
            CockpitDecisionReason(
                category="active_runtime_evidence",
                detail=f"Active runtime modes are present: {active_modes_text}.",
                recommended_next_action="observe_active_runtime",
                blocks_mutation=True,
                source_names=("active_runtime_modes",),
            )
        )
    elif runtime_status.has_active_modes is True:
        reasons.append(
            CockpitDecisionReason(
                category="active_runtime_evidence",
                detail="Runtime status reports active modes without a parsed active-mode list.",
                recommended_next_action="observe_active_runtime",
                blocks_mutation=True,
                source_names=("runtime_status",),
            )
        )
    elif _runtime_status_has_uncertain_activity(runtime_status):
        reasons.append(
            CockpitDecisionReason(
                category="runtime_status_uncertain",
                detail="Runtime status could not determine whether modes are active.",
                recommended_next_action="inspect_runtime_status",
                blocks_mutation=True,
                source_names=("runtime_status",),
            )
        )

    active_team_names: tuple[str, ...] = _collect_active_team_names(team_observations)
    if active_team_names:
        active_team_text: str = ", ".join(active_team_names)
        active_team_source_names: tuple[str, ...] = _collect_active_team_source_names(
            team_observations
        )
        reasons.append(
            CockpitDecisionReason(
                category="active_team_evidence",
                detail=f"Active Team evidence is present for: {active_team_text}.",
                recommended_next_action="inspect_team_evidence",
                blocks_mutation=True,
                source_names=active_team_source_names,
            )
        )

    if (
        goal_mirror_state
        and goal_mirror_state.handoff_state == CodexGoalHandoffState.AWAITING_RALPH
    ):
        reasons.append(
            CockpitDecisionReason(
                category="goal_awaiting_ralph",
                detail=f"Goal {goal_mirror_state.goal_id} is awaiting Ralph handoff.",
                recommended_next_action="prepare_ralph",
                blocks_mutation=False,
                source_names=("goal_mirror_state",),
            )
        )

    if not reasons:
        reasons.append(
            CockpitDecisionReason(
                category="no_blocking_evidence",
                detail="No active runtime, active Team, contradiction, or pending Goal handoff evidence was found.",
                recommended_next_action="observe",
                blocks_mutation=False,
                source_names=("runtime_status", "active_runtime_modes"),
            )
        )

    result: tuple[CockpitDecisionReason, ...] = tuple(reasons)
    return result


def _collect_active_team_names(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Collect Team names whose observations show explicit active evidence.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Team names with explicit active status.
    """
    active_team_names: list[str] = [
        observation.team_name
        for observation in team_observations
        if observation.status in _ACTIVE_TEAM_STATUSES
    ]
    result: tuple[str, ...] = tuple(active_team_names)
    return result


def _collect_active_team_source_names(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Collect decision source names for active Team evidence.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Ordered source names, including blocking proof-layer evidence when present.
    """
    source_names: list[str] = ["team_evidence"]
    seen_source_names: set[str] = {"team_evidence"}
    for observation in team_observations:
        if observation.status not in _ACTIVE_TEAM_STATUSES:
            continue
        for proof_source_name in collect_blocking_team_proof_layer_source_names(
            observation
        ):
            if proof_source_name in seen_source_names:
                continue
            seen_source_names.add(proof_source_name)
            source_names.append(proof_source_name)

    result: tuple[str, ...] = tuple(source_names)
    return result


def _team_observations_include_active_runtime(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> bool:
    """Detect whether Team observations show active Team runtime evidence.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        bool: ``True`` when at least one Team observation has an explicit active status.
    """
    has_active_team: bool = any(
        observation.status in _ACTIVE_TEAM_STATUSES for observation in team_observations
    )
    return has_active_team
