import tomllib
from pathlib import Path
from typing import Final

from omx_remote.schemas.agents.agent_config_schemas import (
    AgentConfig,
    AgentConfigSet,
)

DEFAULT_AGENT_CONFIG_FILENAME: Final[str] = ".agent-remote.toml"
AGENT_CONFIG_TOP_LEVEL_SECTION: Final[str] = "agents"
RESERVED_TOP_LEVEL_SECTIONS: Final[frozenset[str]] = frozenset(
    {AGENT_CONFIG_TOP_LEVEL_SECTION, "commands", "routes"}
)


class AgentConfigLoadError(ValueError):
    """Raised when raw TOML cannot be loaded before schema validation."""


def _resolve_config_path(cwd: str | Path | None, config_path: str | Path | None) -> Path:
    """Resolve the agent config path.

    Args:
        cwd [str | Path | None]: Base working directory for relative config paths.
        config_path [str | Path | None]: Optional config path override.

    Returns:
        Path: Absolute or caller-provided config path to read.
    """
    root_path: Path = Path.cwd() if cwd is None else Path(cwd)
    if config_path is None:
        resolved_path: Path = root_path / DEFAULT_AGENT_CONFIG_FILENAME
        return resolved_path

    candidate_path = Path(config_path)
    if candidate_path.is_absolute():
        resolved_path = candidate_path
        return resolved_path

    resolved_path = root_path / candidate_path
    return resolved_path


def _load_toml_object(config_path: Path) -> dict[str, object]:
    """Load a TOML object from disk.

    Args:
        config_path [Path]: TOML file path to parse.

    Returns:
        dict[str, object]: Parsed TOML root object.
    """
    try:
        config_text: str = config_path.read_text()
        parsed_toml: dict[str, object] = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        raise AgentConfigLoadError(
            f"Agent config at {config_path} contains malformed TOML: {error}"
        ) from error
    except OSError as error:
        raise AgentConfigLoadError(
            f"Agent config at {config_path} could not be read: {error}"
        ) from error

    return parsed_toml


def _validate_top_level_sections(parsed_toml: dict[str, object], config_path: Path) -> None:
    """Validate supported top-level TOML sections.

    Args:
        parsed_toml [dict[str, object]]: Parsed TOML root object.
        config_path [Path]: Source path used for error messages.
    """
    unknown_sections: set[str] = set(parsed_toml) - RESERVED_TOP_LEVEL_SECTIONS
    if unknown_sections:
        unknown_text: str = ", ".join(sorted(unknown_sections))
        raise AgentConfigLoadError(
            f"Agent config at {config_path} contains unsupported top-level section(s): {unknown_text}"
        )


def _load_agent_payloads(parsed_toml: dict[str, object], config_path: Path) -> tuple[AgentConfig, ...]:
    """Load typed agent configurations from a parsed TOML root object.

    Args:
        parsed_toml [dict[str, object]]: Parsed TOML root object.
        config_path [Path]: Source path used for error messages.

    Returns:
        tuple[AgentConfig, ...]: Typed agent configs in TOML order.
    """
    raw_agents_section: object = parsed_toml.get(AGENT_CONFIG_TOP_LEVEL_SECTION, {})
    if not isinstance(raw_agents_section, dict):
        raise AgentConfigLoadError(
            f"Agent config at {config_path} must define [agents] as a TOML table."
        )

    agents: list[AgentConfig] = []
    for agent_id, raw_agent_payload in raw_agents_section.items():
        if not isinstance(agent_id, str):
            raise AgentConfigLoadError(
                f"Agent config at {config_path} contains a non-string agent id."
            )
        if not isinstance(raw_agent_payload, dict):
            raise AgentConfigLoadError(
                f"Agent config at {config_path} must define [agents.{agent_id}] as a TOML table."
            )
        agent_payload: dict[str, object] = {"id": agent_id, **raw_agent_payload}
        agent_config: AgentConfig = AgentConfig.model_validate(agent_payload)
        agents.append(agent_config)

    loaded_agents: tuple[AgentConfig, ...] = tuple(agents)
    return loaded_agents


def load_agent_config(
    cwd: str | Path | None = None,
    config_path: str | Path | None = None,
) -> AgentConfigSet:
    """Load the repo-local TOML agent configuration.

    Args:
        cwd [str | Path | None]: Base working directory for default/relative config paths.
        config_path [str | Path | None]: Optional config path override.

    Returns:
        AgentConfigSet: Typed config set plus non-fatal warnings.
    """
    resolved_config_path: Path = _resolve_config_path(cwd, config_path)
    if not resolved_config_path.exists():
        missing_config = AgentConfigSet(
            config_path=str(resolved_config_path),
            agents=(),
            warnings=(f"No agent config found at {resolved_config_path}.",),
        )
        return missing_config

    parsed_toml: dict[str, object] = _load_toml_object(resolved_config_path)
    _validate_top_level_sections(parsed_toml, resolved_config_path)
    agents: tuple[AgentConfig, ...] = _load_agent_payloads(
        parsed_toml,
        resolved_config_path,
    )
    loaded_config = AgentConfigSet(
        config_path=str(resolved_config_path),
        agents=agents,
        warnings=(),
    )
    return loaded_config
