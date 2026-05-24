from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.agents.agent_config_loader import (
    AgentConfigLoadError,
    load_agent_config,
)
from omx_remote.schemas.agents.agent_config_schemas import (
    AgentConfigSet,
    AgentEffort,
    AgentProvider,
)


def test_minimal_enabled_codex_agent_parses(tmp_path: Path) -> None:
    config_path = tmp_path / ".agent-remote.toml"
    config_path.write_text(
        """
[agents.architect]
enabled = true
provider = "codex"
role = "architect"
model = "gpt-5.5"
effort = "high"
persona = "Design typed boundaries."
""".strip()
    )

    result = load_agent_config(cwd=tmp_path)

    assert result == AgentConfigSet(
        config_path=str(config_path),
        agents=(
            {
                "id": "architect",
                "enabled": True,
                "provider": AgentProvider.CODEX,
                "role": "architect",
                "model": "gpt-5.5",
                "effort": AgentEffort.HIGH,
                "persona": "Design typed boundaries.",
                "routing_hints": (),
            },
        ),
        warnings=(),
    )
    assert result.enabled_agents == result.agents


def test_disabled_agent_is_valid_but_not_enabled(tmp_path: Path) -> None:
    config_path = tmp_path / ".agent-remote.toml"
    config_path.write_text(
        """
[agents.reviewer]
enabled = false
provider = "codex"
role = "reviewer"
model = "gpt-5.5"
effort = "xhigh"
persona = "Review diffs."
""".strip()
    )

    result = load_agent_config(cwd=tmp_path)

    assert result.agents[0].id == "reviewer"
    assert result.agents[0].enabled is False
    assert result.enabled_agents == ()


def test_unknown_agent_key_fails_validation(tmp_path: Path) -> None:
    config_path = tmp_path / ".agent-remote.toml"
    config_path.write_text(
        """
[agents.architect]
enabled = true
provider = "codex"
role = "architect"
model = "gpt-5.5"
effort = "high"
persona = "Design typed boundaries."
unexpected = true
""".strip()
    )

    with pytest.raises(ValidationError, match="unexpected"):
        load_agent_config(cwd=tmp_path)


def test_missing_persona_and_role_errors_are_readable(tmp_path: Path) -> None:
    config_path = tmp_path / ".agent-remote.toml"
    config_path.write_text(
        """
[agents.architect]
enabled = true
provider = "codex"
model = "gpt-5.5"
effort = "high"
""".strip()
    )

    with pytest.raises(ValidationError) as error_info:
        load_agent_config(cwd=tmp_path)

    message = str(error_info.value)
    assert "role" in message
    assert "persona" in message


def test_provider_enum_rejects_unsupported_value(tmp_path: Path) -> None:
    config_path = tmp_path / ".agent-remote.toml"
    config_path.write_text(
        """
[agents.architect]
enabled = true
provider = "other"
role = "architect"
model = "gpt-5.5"
effort = "high"
persona = "Design typed boundaries."
""".strip()
    )

    with pytest.raises(ValidationError, match="provider"):
        load_agent_config(cwd=tmp_path)


def test_missing_config_returns_empty_config_with_warning(tmp_path: Path) -> None:
    result = load_agent_config(cwd=tmp_path)

    assert result.agents == ()
    assert result.warnings == (
        f"No agent config found at {tmp_path / '.agent-remote.toml'}.",
    )


def test_malformed_toml_raises_config_load_error(tmp_path: Path) -> None:
    config_path = tmp_path / ".agent-remote.toml"
    config_path.write_text("[agents.architect\n")

    with pytest.raises(AgentConfigLoadError, match="malformed TOML"):
        load_agent_config(cwd=tmp_path)


def test_explicit_config_path_is_resolved_from_cwd(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "agents.toml"
    config_path.write_text(
        """
[agents.implementer]
enabled = true
provider = "codex"
role = "implementer"
model = "gpt-5.5"
effort = "medium"
persona = "Implement with tests."
""".strip()
    )

    result = load_agent_config(cwd=tmp_path, config_path=Path("config/agents.toml"))

    assert result.config_path == str(config_path)
    assert result.agents[0].id == "implementer"
