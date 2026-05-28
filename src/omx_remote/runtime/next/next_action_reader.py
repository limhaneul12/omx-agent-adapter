from pathlib import Path
from shlex import quote as quote_shell_token

from omx_remote.runtime.cockpit.snapshot.reader import read_cockpit_snapshot
from omx_remote.runtime.routes.route_policy_engine import build_route_policy_result
from omx_remote.schemas.cockpit.snapshot_schemas import (
    CockpitSnapshot,
    CockpitSnapshotRequest,
)
from omx_remote.schemas.next.next_action_schemas import (
    NextActionRequest,
    NextActionResult,
)
from omx_remote.schemas.routes.route_policy_schemas import (
    RouteName,
    RoutePolicyResult,
    RouteRecommendation,
)


async def read_next_action(request: NextActionRequest) -> NextActionResult:
    """Read cockpit and route evidence to recommend the next safe action.

    Args:
        request [NextActionRequest]: Repo, optional task, and optional Team names.

    Returns:
        NextActionResult: Read-only recommendation with evidence links.
    """
    cockpit_snapshot: CockpitSnapshot = await read_cockpit_snapshot(
        request=_cockpit_request_from_next(request)
    )
    route_policy: RoutePolicyResult | None = None
    if request.task is not None:
        route_policy = build_route_policy_result(
            task=request.task,
            cwd=Path(request.repo_root),
            capabilities=cockpit_snapshot.capabilities,
            agent_summary=cockpit_snapshot.configured_agents,
            recipe_summary=cockpit_snapshot.command_recipes,
            safe_to_mutate=cockpit_snapshot.safe_to_mutate,
            active_runtime_modes=cockpit_snapshot.active_runtime_modes,
        )

    result: NextActionResult = build_next_action_result(
        cockpit_snapshot=cockpit_snapshot,
        task=request.task,
        route_policy=route_policy,
    )
    return result


def build_next_action_result(
    cockpit_snapshot: CockpitSnapshot,
    task: str | None = None,
    route_policy: RoutePolicyResult | None = None,
) -> NextActionResult:
    """Compose existing cockpit and route evidence into one read-only result.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        task [str | None]: Optional task text to route.
        route_policy [RoutePolicyResult | None]: Optional precomputed route policy.

    Returns:
        NextActionResult: Cross-lane next-action recommendation.
    """
    selected_action: str = _select_recommended_action(cockpit_snapshot, route_policy)
    route_recommendations: tuple[RouteRecommendation, ...] = ()
    if route_policy is not None:
        route_recommendations = route_policy.recommendations

    why: tuple[str, ...] = _collect_why(cockpit_snapshot, route_policy)
    source_names: tuple[str, ...] = _collect_source_names(cockpit_snapshot, route_policy)
    blocked_actions: tuple[str, ...] = _collect_blocked_actions(
        cockpit_snapshot,
        route_policy,
    )
    warnings: tuple[str, ...] = _collect_warnings(cockpit_snapshot, route_policy)
    recommended_commands: tuple[str, ...] = _build_recommended_commands(
        cockpit_snapshot=cockpit_snapshot,
        task=task,
        route_policy=route_policy,
    )
    requires_review: bool = (
        not cockpit_snapshot.safe_to_mutate
        or bool(cockpit_snapshot.contradictions)
        or any(reason.blocks_mutation for reason in cockpit_snapshot.decision_reasons)
    )
    summary: str = _build_summary(selected_action, cockpit_snapshot, route_policy)

    result = NextActionResult(
        recommended_action=selected_action,
        safe_to_mutate=cockpit_snapshot.safe_to_mutate,
        requires_review=requires_review,
        summary=summary,
        why=why,
        source_names=source_names,
        recommended_commands=recommended_commands,
        blocked_actions=blocked_actions,
        route_recommendations=route_recommendations,
        warnings=warnings,
    )
    return result


def _cockpit_request_from_next(request: NextActionRequest) -> CockpitSnapshotRequest:
    """Convert a next-action request into a cockpit snapshot request.

    Args:
        request [NextActionRequest]: Next-action request boundary.

    Returns:
        CockpitSnapshotRequest: Cockpit read request with matching repo and teams.
    """
    cockpit_request = CockpitSnapshotRequest(
        repo_root=request.repo_root,
        team_names=request.team_names,
    )
    return cockpit_request


def _select_recommended_action(
    cockpit_snapshot: CockpitSnapshot,
    route_policy: RoutePolicyResult | None,
) -> str:
    """Choose the top-level next-action marker.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        str: Stable next-action marker.
    """
    if cockpit_snapshot.contradictions:
        action: str = "inspect_runtime_contradiction"
        return action
    if not cockpit_snapshot.safe_to_mutate:
        action = cockpit_snapshot.recommended_next_action
        return action
    if route_policy is not None and route_policy.recommendations:
        top_recommendation: RouteRecommendation = route_policy.recommendations[0]
        if top_recommendation.route == RouteName.OMX_ULTRAGOAL:
            action = "prepare_ultragoal_handoff"
            return action
        action = "inspect_route_recommendation"
        return action

    action = cockpit_snapshot.recommended_next_action
    return action


def _collect_why(
    cockpit_snapshot: CockpitSnapshot,
    route_policy: RoutePolicyResult | None,
) -> tuple[str, ...]:
    """Collect human-readable reasons for the next-action result.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        tuple[str, ...]: Ordered reason strings.
    """
    reasons: list[str] = [reason.detail for reason in cockpit_snapshot.decision_reasons]
    if route_policy is not None and route_policy.recommendations:
        top_recommendation: RouteRecommendation = route_policy.recommendations[0]
        reasons.append(top_recommendation.reason)
    if not reasons:
        reasons.append("Cockpit and route policy returned no blocking evidence.")

    result: tuple[str, ...] = tuple(reasons)
    return result


def _collect_source_names(
    cockpit_snapshot: CockpitSnapshot,
    route_policy: RoutePolicyResult | None,
) -> tuple[str, ...]:
    """Collect source names used by cockpit and route policy.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        tuple[str, ...]: Ordered unique source names.
    """
    source_names: list[str] = []
    seen_source_names: set[str] = set()
    for decision_reason in cockpit_snapshot.decision_reasons:
        _append_unique(source_names, seen_source_names, decision_reason.source_names)

    if route_policy is not None:
        _append_unique(source_names, seen_source_names, ("route_policy",))

    if not source_names:
        source_names.append("cockpit")

    result: tuple[str, ...] = tuple(source_names)
    return result


def _collect_blocked_actions(
    cockpit_snapshot: CockpitSnapshot,
    route_policy: RoutePolicyResult | None,
) -> tuple[str, ...]:
    """Collect actions that should not be run before inspection.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        tuple[str, ...]: Human-readable blocked action descriptions.
    """
    blocked_actions: list[str] = []
    if not cockpit_snapshot.safe_to_mutate:
        blocked_actions.append("mutating runtime launch/cleanup commands")
    if route_policy is not None:
        for blocked_alternative in route_policy.blocked_alternatives:
            blocker_text: str = "; ".join(blocked_alternative.blocked_by)
            blocked_actions.append(f"{blocked_alternative.route}: {blocker_text}")

    result: tuple[str, ...] = tuple(blocked_actions)
    return result


def _collect_warnings(
    cockpit_snapshot: CockpitSnapshot,
    route_policy: RoutePolicyResult | None,
) -> tuple[str, ...]:
    """Collect warnings from cockpit and route-policy evidence.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        tuple[str, ...]: Combined warning strings.
    """
    warnings: tuple[str, ...] = cockpit_snapshot.warnings
    if route_policy is not None:
        warnings = (*warnings, *route_policy.warnings)

    return warnings


def _build_recommended_commands(
    cockpit_snapshot: CockpitSnapshot,
    task: str | None,
    route_policy: RoutePolicyResult | None,
) -> tuple[str, ...]:
    """Build read-only or dry-run-first command suggestions.

    Args:
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        task [str | None]: Optional task text.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        tuple[str, ...]: Command strings that do not execute native mutation.
    """
    repo_root: str = _quote_shell_token(cockpit_snapshot.repo_root)
    commands: list[str] = [f"agent-remote cockpit snapshot --cwd {repo_root} --json"]
    if task is not None:
        commands.append(
            f"agent-remote route recommend --cwd {repo_root} --task {_quote_shell_token(task)} --json"
        )
    if route_policy is not None and route_policy.recommendations:
        top_recommendation: RouteRecommendation = route_policy.recommendations[0]
        if top_recommendation.route == RouteName.OMX_ULTRAGOAL:
            commands.extend(
                (
                    f"agent-remote ultragoal status --cwd {repo_root} --json",
                    f"agent-remote preflight route omx-ultragoal --cwd {repo_root} --json",
                )
            )
        elif top_recommendation.route == RouteName.PROJECT_COMMAND and top_recommendation.command_id:
            command_id: str = _quote_shell_token(top_recommendation.command_id)
            commands.extend(
                (
                    f"agent-remote preflight run {command_id} --cwd {repo_root} --json",
                    f"agent-remote run {command_id} --cwd {repo_root} --dry-run --json",
                )
            )
        else:
            route_id: str = top_recommendation.route.replace("_", "-")
            commands.append(
                f"agent-remote preflight route {route_id} --cwd {repo_root} --json"
            )

    result: tuple[str, ...] = tuple(commands)
    return result


def _build_summary(
    selected_action: str,
    cockpit_snapshot: CockpitSnapshot,
    route_policy: RoutePolicyResult | None,
) -> str:
    """Build the compact next-action summary.

    Args:
        selected_action [str]: Chosen next-action marker.
        cockpit_snapshot [CockpitSnapshot]: Read-only cockpit evidence.
        route_policy [RoutePolicyResult | None]: Optional route policy evidence.

    Returns:
        str: Human-readable result summary.
    """
    if cockpit_snapshot.contradictions:
        summary: str = "Inspect cockpit contradictions before route selection or mutation."
        return summary
    if not cockpit_snapshot.safe_to_mutate:
        summary = "Cockpit evidence blocks mutation; inspect the blocking evidence first."
        return summary
    if route_policy is not None and route_policy.recommendations:
        top_recommendation: RouteRecommendation = route_policy.recommendations[0]
        summary = f"Next read-only route check is {top_recommendation.route}."
        return summary

    summary = f"Next safe action is {selected_action}."
    return summary


def _append_unique(
    target: list[str],
    seen_values: set[str],
    values: tuple[str, ...],
) -> None:
    """Append unseen values to a list in order.

    Args:
        target [list[str]]: Mutable ordered target list.
        seen_values [set[str]]: Mutable set of values already appended.
        values [tuple[str, ...]]: Candidate values to append.
    """
    for value in values:
        if value in seen_values:
            continue
        seen_values.add(value)
        target.append(value)


def _quote_shell_token(value: str) -> str:
    """Quote a value for display as one shell token.

    Args:
        value [str]: Value to quote.

    Returns:
        str: Shell-safe token text.
    """
    quoted_value: str = quote_shell_token(value)
    return quoted_value
