from pathlib import Path

from pydantic import ValidationError

from omx_remote.runtime.agents.agent_config_loader import (
    AgentConfigLoadError,
    load_agent_config,
)
from omx_remote.schemas.agents.agent_config_schemas import AgentConfigSet
from omx_remote.schemas.cockpit.capability_snapshot_schemas import (
    CockpitAgentConfigSummary,
)


def summarize_cockpit_agent_config(cwd: str | Path) -> CockpitAgentConfigSummary:
    """Summarize repo-local TOML agent config for cockpit snapshots.

    Args:
        cwd [str | Path]: Repository root used to resolve `.agent-remote.toml`.

    Returns:
        CockpitAgentConfigSummary: Agent config counts and warnings.
    """
    try:
        config: AgentConfigSet = load_agent_config(cwd=cwd)
    except (AgentConfigLoadError, ValidationError) as error:
        config_path: str = str(Path(cwd) / ".agent-remote.toml")
        summary = CockpitAgentConfigSummary(
            config_path=config_path,
            total_count=0,
            enabled_count=0,
            disabled_count=0,
            enabled_agent_ids=(),
            warnings=(f"Agent config could not be loaded: {error}",),
        )
        return summary

    enabled_agent_ids: tuple[str, ...] = tuple(agent.id for agent in config.enabled_agents)
    total_count: int = len(config.agents)
    enabled_count: int = len(config.enabled_agents)
    summary = CockpitAgentConfigSummary(
        config_path=config.config_path,
        total_count=total_count,
        enabled_count=enabled_count,
        disabled_count=total_count - enabled_count,
        enabled_agent_ids=enabled_agent_ids,
        warnings=config.warnings,
    )
    return summary
