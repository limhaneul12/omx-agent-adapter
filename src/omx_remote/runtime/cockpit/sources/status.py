from omx_remote.runtime.cockpit.snapshot.decisions import (
    _runtime_status_has_uncertain_activity,
)
from omx_remote.runtime.cockpit.team_evidence.discovery import LinkedTeamDiscoveryResult
from omx_remote.runtime.cockpit.team_evidence.summary import (
    _collect_team_observation_warnings,
)
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitPullRequestObservation,
    CockpitStatusSourceObservation,
    CockpitStatusSourceState,
    CockpitTeamObservation,
)
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalMirrorState
from omx_remote.schemas.runtime_status_schemas import ActiveRuntimeModes, RuntimeStatus


def _build_status_sources(
    goal_mirror_state: CodexGoalMirrorState | None,
    team_discovery: LinkedTeamDiscoveryResult,
    selected_team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
    runtime_status: RuntimeStatus,
    active_runtime_modes: ActiveRuntimeModes,
    ultrawork_warnings: tuple[str, ...],
    pull_request_status: CockpitPullRequestObservation,
) -> tuple[CockpitStatusSourceObservation, ...]:
    """Build read-only source observations for the all-status cockpit.

    Args:
        goal_mirror_state [CodexGoalMirrorState | None]: Optional Goal mirror evidence.
        team_discovery [LinkedTeamDiscoveryResult]: Team-name discovery evidence.
        selected_team_names [tuple[str, ...]]: Team names selected for evidence reads.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.
        runtime_status [RuntimeStatus]: Normalized runtime status snapshot.
        active_runtime_modes [ActiveRuntimeModes]: Active runtime modes snapshot.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork source warnings.
        pull_request_status [CockpitPullRequestObservation]: GitHub PR/review/check evidence.

    Returns:
        tuple[CockpitStatusSourceObservation, ...]: Stable source status observations.
    """
    first_team_discovery_source: str | None = None
    if team_discovery.inspected_sources:
        first_team_discovery_source = team_discovery.inspected_sources[0]

    goal_status: CockpitStatusSourceState = CockpitStatusSourceState.MISSING
    goal_detail = "No adapter-owned Goal mirror state was found."
    goal_evidence_path: str | None = None
    if goal_mirror_state is not None:
        goal_status = CockpitStatusSourceState.OBSERVED
        goal_detail = f"Goal mirror state for {goal_mirror_state.goal_id} was read."
        goal_evidence_path = (
            f"{goal_mirror_state.working_directory}/.comx-agent/state/codex-goal.json"
        )
    elif team_discovery.goal_mirror_failure is not None:
        goal_status = CockpitStatusSourceState.FAILED
        goal_detail = team_discovery.goal_mirror_failure
        goal_evidence_path = first_team_discovery_source

    team_discovery_status: CockpitStatusSourceState = CockpitStatusSourceState.MISSING
    team_discovery_detail = "No exact linked Team names were discovered."
    if team_discovery.discovered_team_names:
        team_discovery_status = CockpitStatusSourceState.OBSERVED
        discovered_text: str = ", ".join(team_discovery.discovered_team_names)
        team_discovery_detail = f"Discovered linked Team names: {discovered_text}."
    elif team_discovery.warnings:
        team_discovery_status = CockpitStatusSourceState.FAILED
        team_discovery_detail = (
            "Team discovery inspected persisted state with warnings."
        )

    team_selection_status: CockpitStatusSourceState = CockpitStatusSourceState.MISSING
    team_selection_detail = "No explicit or discovered Team names were selected."
    if selected_team_names:
        team_selection_status = CockpitStatusSourceState.OBSERVED
        selected_text: str = ", ".join(selected_team_names)
        team_selection_detail = (
            f"Selected Team names for evidence reads: {selected_text}."
        )

    runtime_status_source_state: CockpitStatusSourceState = (
        CockpitStatusSourceState.OBSERVED
    )
    if _runtime_status_has_uncertain_activity(runtime_status):
        runtime_status_source_state = CockpitStatusSourceState.UNKNOWN

    active_modes_detail = "No active runtime modes were reported."
    if active_runtime_modes.active_modes:
        active_modes_text: str = ", ".join(active_runtime_modes.active_modes)
        active_modes_detail = (
            f"Active runtime modes were reported: {active_modes_text}."
        )

    ultrawork_status: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    ultrawork_detail = "Ultrawork state was classified."
    if ultrawork_warnings:
        ultrawork_status = CockpitStatusSourceState.FAILED
        ultrawork_detail = "Ultrawork state was classified with warnings."

    sources: tuple[CockpitStatusSourceObservation, ...] = (
        CockpitStatusSourceObservation(
            name="runtime_status",
            status=runtime_status_source_state,
            detail=runtime_status.summary or "Runtime status was read.",
        ),
        CockpitStatusSourceObservation(
            name="active_runtime_modes",
            status=CockpitStatusSourceState.OBSERVED,
            detail=active_modes_detail,
        ),
        CockpitStatusSourceObservation(
            name="goal_mirror_state",
            status=goal_status,
            detail=goal_detail,
            evidence_path=goal_evidence_path,
        ),
        CockpitStatusSourceObservation(
            name="team_discovery",
            status=team_discovery_status,
            detail=team_discovery_detail,
            evidence_path=first_team_discovery_source,
        ),
        CockpitStatusSourceObservation(
            name="team_selection",
            status=team_selection_status,
            detail=team_selection_detail,
        ),
        _build_team_evidence_source(
            selected_team_names=selected_team_names,
            team_observations=team_observations,
        ),
        _build_github_pull_request_source(pull_request_status),
        CockpitStatusSourceObservation(
            name="ultrawork_state",
            status=ultrawork_status,
            detail=ultrawork_detail,
        ),
    )
    return sources


def _build_github_pull_request_source(
    pull_request_status: CockpitPullRequestObservation,
) -> CockpitStatusSourceObservation:
    """Build the GitHub PR/review/check source observation.

    Args:
        pull_request_status [CockpitPullRequestObservation]: Pull request evidence.

    Returns:
        CockpitStatusSourceObservation: Source status for PR/review/check evidence.
    """
    source_status: CockpitStatusSourceState = CockpitStatusSourceState.OBSERVED
    if pull_request_status.status == "no_open_pull_request":
        source_status = CockpitStatusSourceState.MISSING
    elif pull_request_status.status == "unavailable":
        source_status = CockpitStatusSourceState.SKIPPED
    elif pull_request_status.warnings:
        source_status = CockpitStatusSourceState.FAILED

    source = CockpitStatusSourceObservation(
        name="github_pr_status",
        status=source_status,
        detail=pull_request_status.detail,
        evidence_path=pull_request_status.url,
    )
    return source


def _build_team_evidence_source(
    selected_team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
) -> CockpitStatusSourceObservation:
    """Build the Team evidence source observation.

    Args:
        selected_team_names [tuple[str, ...]]: Team names selected for evidence reads.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        CockpitStatusSourceObservation: Source status for Team evidence reads.
    """
    if not selected_team_names:
        skipped_source = CockpitStatusSourceObservation(
            name="team_evidence",
            status=CockpitStatusSourceState.SKIPPED,
            detail="No Team names were selected for evidence reads.",
        )
        return skipped_source

    selected_team_text: str = ", ".join(selected_team_names)
    if not team_observations:
        failed_source = CockpitStatusSourceObservation(
            name="team_evidence",
            status=CockpitStatusSourceState.FAILED,
            detail=f"Team names were selected but no Team evidence was read: {selected_team_text}.",
        )
        return failed_source

    warnings: tuple[str, ...] = _collect_team_observation_warnings(team_observations)
    if warnings:
        warning_source = CockpitStatusSourceObservation(
            name="team_evidence",
            status=CockpitStatusSourceState.FAILED,
            detail=f"Team evidence was read with warnings for: {selected_team_text}.",
        )
        return warning_source

    observed_team_text: str = ", ".join(
        observation.team_name for observation in team_observations
    )
    observed_source = CockpitStatusSourceObservation(
        name="team_evidence",
        status=CockpitStatusSourceState.OBSERVED,
        detail=f"Team evidence was read for: {observed_team_text}.",
    )
    return observed_source


def _build_top_level_warnings(
    warnings: tuple[str, ...],
    ultrawork_warnings: tuple[str, ...],
    team_names: tuple[str, ...],
    team_observations: tuple[CockpitTeamObservation, ...],
) -> tuple[str, ...]:
    """Build top-level warning labels from cockpit degradation evidence.

    Args:
        warnings [tuple[str, ...]]: Discovery or source warnings.
        ultrawork_warnings [tuple[str, ...]]: Ultrawork read warnings.
        team_names [tuple[str, ...]]: Team names selected for Team evidence reads.
        team_observations [tuple[CockpitTeamObservation, ...]]: Team evidence read from Team surfaces.

    Returns:
        tuple[str, ...]: Stable ordered top-level warnings.
    """
    top_level_warnings: list[str] = [
        *warnings,
        *ultrawork_warnings,
        *_collect_team_observation_warnings(team_observations),
    ]
    if team_names and not team_observations:
        top_level_warnings.append(
            "Team names were selected but no Team evidence observations were produced."
        )

    result: tuple[str, ...] = tuple(top_level_warnings)
    return result
