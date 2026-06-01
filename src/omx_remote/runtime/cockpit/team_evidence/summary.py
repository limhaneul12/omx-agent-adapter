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
        summary_parts.append(
            f"{observation.team_name}: {observation.status} ({phase_text}), "
            f"{observation.task_count} tasks, {observation.event_count} events, "
            f"{worker_count} worker statuses"
        )

    summary: str = "; ".join(summary_parts)
    return summary


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
