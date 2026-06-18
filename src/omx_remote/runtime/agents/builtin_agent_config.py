from omx_remote.schemas.agents.agent_config_schemas import (
    AgentConfig,
    AgentConfigSet,
)
from omx_remote.shared.omx_enums.agent_enums import AgentEffort, AgentProvider


def build_builtin_agent_config(config_path: str) -> AgentConfigSet:
    """Build adapter-owned agent defaults for builtin command recipes.

    Args:
        config_path [str]: Synthetic path describing why defaults were used.

    Returns:
        AgentConfigSet: Builtin agent configuration for adapter recipes.
    """
    agents: tuple[AgentConfig, ...] = (
        AgentConfig(
            id="route_strategist",
            enabled=True,
            provider=AgentProvider.CODEX,
            role="omx-route-strategist",
            model="gpt-5.5",
            effort=AgentEffort.XHIGH,
            persona=(
                "Decide the safest Codex/OMX route for a task. Read cockpit, "
                "next-action, preflight, runtime, dirty-worktree, configured-agent, "
                "and command-catalog evidence before recommending any mutation."
            ),
            routing_hints=(
                "route-next",
                "discovery-gate",
                "cockpit",
                "preflight",
                "safe-to-mutate",
                "blocked-alternatives",
            ),
        ),
        AgentConfig(
            id="research_analyst",
            enabled=True,
            provider=AgentProvider.CODEX,
            role="source-backed-research-analyst",
            model="gpt-5.5",
            effort=AgentEffort.XHIGH,
            persona=(
                "Produce bounded, citation-backed research briefs. Prefer "
                "official/upstream/current sources, label confidence, separate "
                "evidence from inference, and surface contradictions."
            ),
            routing_hints=(
                "research-brief",
                "idea-to-prd",
                "dependency-risk",
                "citations",
            ),
        ),
        AgentConfig(
            id="implementation_architect",
            enabled=True,
            provider=AgentProvider.CODEX,
            role="implementation-kickoff-architect",
            model="gpt-5.5",
            effort=AgentEffort.XHIGH,
            persona=(
                "Turn accepted PRDs, briefs, and broad objectives into "
                "execution-ready slices. Choose between Codex-only, Goal, Ralph, "
                "Team, UltraGoal, and Ultrawork without taking ownership of "
                "native runtime execution."
            ),
            routing_hints=(
                "implementation-kickoff",
                "ultragoal",
                "team-planning",
                "migration",
                "runtime-handoff",
            ),
        ),
        AgentConfig(
            id="integration_steward",
            enabled=True,
            provider=AgentProvider.CODEX,
            role="team-and-integration-steward",
            model="gpt-5.5",
            effort=AgentEffort.XHIGH,
            persona=(
                "Read Team, subagent, and run-ledger evidence without mutating "
                "runtime state. Summarize proof layers, blockers, missing "
                "evidence, accepted outputs, conflict matrices, and integration "
                "order."
            ),
            routing_hints=(
                "team-sync",
                "integration-plan",
                "conflict-resolution",
                "run-ledger",
            ),
        ),
        AgentConfig(
            id="quality_gatekeeper",
            enabled=True,
            provider=AgentProvider.CODEX,
            role="review-and-release-gatekeeper",
            model="gpt-5.5",
            effort=AgentEffort.XHIGH,
            persona=(
                "Run strict review and release-readiness gates. Check correctness, "
                "tests, security, performance, maintainability, docs, run evidence, "
                "and Alexandria closeout needs."
            ),
            routing_hints=("review-gate", "release-readiness", "docs"),
        ),
    )
    config = AgentConfigSet(
        config_path=config_path,
        agents=agents,
        warnings=("Using adapter-owned builtin agent defaults.",),
    )
    return config
