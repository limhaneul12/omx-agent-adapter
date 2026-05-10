from omx_remote.schemas.cockpit.snapshot_schemas import CockpitTeamObservation


def _summarize_team_observations(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> str:
    """Summarize Team observations for the Ralph -> Team cockpit lane.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        str: Compact human-readable Team evidence summary.
    """
    summary_parts: list[str] = []
    for observation in team_observations:
        phase_text: str = "no phase"
        if observation.phase is not None:
            phase_text = observation.phase
        worker_count: int = len(observation.worker_statuses)
        proof_layer_text: str = _summarize_proof_layers(observation)
        summary_parts.append(
            f"{observation.team_name}: {observation.status} ({phase_text}), "
            f"{observation.task_count} tasks, {observation.event_count} events, "
            f"{worker_count} worker statuses, {proof_layer_text}"
        )

    summary: str = "; ".join(summary_parts)
    return summary


def _summarize_proof_layers(observation: CockpitTeamObservation) -> str:
    """Summarize Team proof layers for lane text.

    Args:
        observation [CockpitTeamObservation]: Team observation with proof layers.

    Returns:
        str: Compact proof-layer summary text.
    """
    if not observation.proof_layers:
        return "no proof layers"

    proof_parts: list[str] = [
        f"{_proof_layer_summary_name(proof_layer.layer)}={proof_layer.state}"
        for proof_layer in observation.proof_layers
    ]
    proof_summary: str = "proof " + ", ".join(proof_parts)
    return proof_summary


def _proof_layer_summary_name(layer_name: str) -> str:
    """Return a summary-safe proof-layer name that preserves evidence basis.

    Args:
        layer_name [str]: Raw proof-layer name.

    Returns:
        str: Summary-safe proof-layer name.
    """
    if layer_name == "assignment_import":
        return "task_owner_assignment"
    return layer_name


def _collect_team_observation_warnings(
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Collect warnings from Team observations.

    Args:
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Flattened warning texts.
    """
    warnings: list[str] = []
    for observation in team_observations:
        warnings.extend(observation.warnings)

    result: tuple[str, ...] = tuple(warnings)
    return result
