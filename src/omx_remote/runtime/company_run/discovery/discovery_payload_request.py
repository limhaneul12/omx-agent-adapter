"""Request-derived discovery-payload fields."""

from enum import StrEnum

from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunExecutionRequest,
)
from omx_remote.shared.omx_enums.company_run_discovery_enums import (
    COMPANY_RUN_DECISION_BOUNDARY_MARKERS,
    COMPANY_RUN_NON_GOAL_MARKERS,
)
from omx_remote.shared.omx_enums.discovery_gate_enums import (
    DiscoveryGateDelegationLevel,
    DiscoveryGateVerdict,
)

from .discovery_payload_verdict import company_run_discovery_should_continue


def _settled_facts_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Build settled discovery facts from the request and verdict.

    Args:
        request: Company-run execution request containing objective and profile.
        verdict: Discovery verdict selected from Gate 0.

    Returns:
        tuple[str, ...]: Settled facts for the discovery packet.
    """
    facts = (
        f"Objective supplied by caller: {request.objective}",
        f"Company-run discovery profile: {request.discovery_profile}",
    )
    if company_run_discovery_should_continue(verdict=verdict):
        facts = (*facts, "The objective includes enough explicit boundary signals for Gate 0.")
    return facts


def _non_goals_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Extract or synthesize non-goals for the discovery packet.

    Args:
        request: Company-run execution request containing objective text.
        verdict: Discovery verdict selected from Gate 0.

    Returns:
        tuple[str, ...]: Non-goals captured for decision context.
    """
    if _contains_marker_value(
        text=request.objective.casefold(),
        markers=COMPANY_RUN_NON_GOAL_MARKERS,
    ):
        non_goals = (f"Preserve stated non-goals from objective: {request.objective}",)
        return non_goals
    if verdict in {
        DiscoveryGateVerdict.REROUTE_SMALL_TASK,
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW,
        DiscoveryGateVerdict.NO_BUILD,
    }:
        non_goals = ("Do not launch Team or implementation before Gate 0 is resolved.",)
        return non_goals
    empty_non_goals: tuple[str, ...] = ()
    return empty_non_goals


def _decision_boundaries_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Extract or synthesize decision boundaries for the discovery packet.

    Args:
        request: Company-run execution request containing objective text.
        verdict: Discovery verdict selected from Gate 0.

    Returns:
        tuple[str, ...]: Boundary statements for the discovery packet.
    """
    if _contains_marker_value(
        text=request.objective.casefold(),
        markers=COMPANY_RUN_DECISION_BOUNDARY_MARKERS,
    ):
        boundaries = (
            f"Preserve explicit decision boundaries from objective: {request.objective}",
        )
        return boundaries
    if verdict in {
        DiscoveryGateVerdict.REROUTE_SMALL_TASK,
        DiscoveryGateVerdict.RUN_DEEP_INTERVIEW,
        DiscoveryGateVerdict.NO_BUILD,
    }:
        boundaries = ("Stop before expensive company-run work until boundaries are clear.",)
        return boundaries
    empty_boundaries: tuple[str, ...] = ()
    return empty_boundaries


def _acceptance_criteria_for_request(
    request: CompanyRunExecutionRequest,
    verdict: DiscoveryGateVerdict,
) -> tuple[str, ...]:
    """Build acceptance criteria for the discovery packet.

    Args:
        request: Company-run execution request containing objectives.
        verdict: Discovery verdict selected from Gate 0.

    Returns:
        tuple[str, ...]: Acceptance criteria inferred for this request.
    """
    if company_run_discovery_should_continue(verdict=verdict):
        criteria = (f"Produce the artifacts and evidence requested by: {request.objective}",)
        return criteria
    if verdict == DiscoveryGateVerdict.NO_BUILD:
        criteria = ("No implementation or Team launch occurs for the stopped request.",)
        return criteria
    empty_criteria: tuple[str, ...] = ()
    return empty_criteria


def _delegation_level_for_request(
    request: CompanyRunExecutionRequest,
) -> DiscoveryGateDelegationLevel:
    """Map request autonomy to discovery delegation level.

    Args:
        request: Company-run execution request containing autonomy mode.

    Returns:
        DiscoveryGateDelegationLevel: Mapped delegation level for Gate 0.
    """
    if request.autonomy == "agent":
        level = DiscoveryGateDelegationLevel.FULL_DELEGATE_TO_ORCHESTRATOR
        return level
    level = DiscoveryGateDelegationLevel.UNSPECIFIED
    return level


def _contains_marker_value(text: str, markers: tuple[StrEnum, ...]) -> bool:
    """Return whether one enum-like marker value appears in text.

    Args:
        text [str]: Case-folded objective text.
        markers [tuple[StrEnum, ...]]: Marker enum values with string values.

    Returns:
        bool: Whether any marker value matched.
    """
    matched = any(marker.value in text for marker in markers)
    return matched
