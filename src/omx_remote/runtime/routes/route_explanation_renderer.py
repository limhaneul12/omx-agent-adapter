from omx_remote.schemas.routes.route_policy_schemas import RouteExplanation, RouteName

_ROUTE_EXPLANATIONS: dict[RouteName, tuple[str, str, str | None]] = {
    RouteName.CODEX_EXEC: (
        "Use Codex directly for scoped implementation, review, or verification.",
        "Small or medium tasks where one agent can complete and verify the change.",
        "codex-exec",
    ),
    RouteName.CODEX_SUBAGENT: (
        "Use Codex native subagents for bounded independent parallel subtasks.",
        "Parallel file-owner work when configured agents are available.",
        None,
    ),
    RouteName.OMX_EXEC: (
        "Use OMX directly when the native runtime command is the clearest interface.",
        "OMX-owned status, setup, or control operations.",
        None,
    ),
    RouteName.OMX_ULTRAGOAL: (
        "Use native OMX UltraGoal for durable multi-goal roadmap execution.",
        "Large roadmap or brief-driven work that needs ledger checkpoints.",
        "omx-ultragoal",
    ),
    RouteName.OMX_TEAM: (
        "Use OMX Team for coordinated worker fanout after mutation preflight passes.",
        "Parallel implementation across workers with a healthy leader runtime.",
        "omx-team",
    ),
    RouteName.OMX_RALPH: (
        "Use Ralph when an approved plan needs a persistent owner-verifier loop.",
        "Plan-driven implementation that needs repeated verification.",
        None,
    ),
    RouteName.PROJECT_COMMAND: (
        "Use a project-owned composed command recipe when a tested recipe matches the task.",
        "Repeatable review, implementation, or verification flows captured in the command catalog.",
        None,
    ),
    RouteName.PROMPT_ONLY: (
        "Use a prompt-only route when no native runtime surface is safe or available.",
        "Manual handoff or prompt-file tasks without executable support.",
        None,
    ),
    RouteName.LOCAL_VERIFY: (
        "Use local verification for deterministic test, lint, typecheck, and smoke gates.",
        "Validation-only tasks with no runtime orchestration requirement.",
        None,
    ),
    RouteName.MANUAL_HANDOFF: (
        "Use manual handoff when required authority or interactive approval is missing.",
        "Credential-gated, destructive, or external-production operations.",
        None,
    ),
}


def normalize_route_name(route: str) -> RouteName:
    """Normalize a CLI route token to a route enum.

    Args:
        route [str]: Route token using hyphens or underscores.

    Returns:
        RouteName: Normalized route name.
    """
    normalized_route: str = route.strip().replace("-", "_")
    route_name = RouteName(normalized_route)
    return route_name


def explain_route(route: str | RouteName) -> RouteExplanation:
    """Build a route explanation.

    Args:
        route [str | RouteName]: Route enum or CLI token.

    Returns:
        RouteExplanation: Explanation for humans and agents.
    """
    if isinstance(route, RouteName):
        route_name: RouteName = route
    else:
        route_name = normalize_route_name(route)
    summary, typical_use, preflight_route = _ROUTE_EXPLANATIONS[route_name]
    explanation = RouteExplanation(
        route=route_name,
        summary=summary,
        typical_use=typical_use,
        preflight_route=preflight_route,
    )
    return explanation


def render_route_policy_human(result_summary: str, route_lines: tuple[str, ...]) -> str:
    """Render a compact human route-policy summary.

    Args:
        result_summary [str]: Header summary.
        route_lines [tuple[str, ...]]: Route lines to join.

    Returns:
        str: Human-readable route policy output.
    """
    rendered_output: str = "\n".join((result_summary, *route_lines))
    return rendered_output
