from pathlib import Path

from omx_remote.schemas.agents.codex_agent_materialization_schemas import (
    CodexAgentCapabilitySnapshot,
)

_REQUIRED_AGENT_TOML_MARKERS: tuple[str, ...] = (
    'name = "',
    'description = "',
    'model = "',
    'model_reasoning_effort = "',
    "developer_instructions",
)


def _default_codex_home() -> Path:
    """Resolve the default Codex home path.

    Returns:
        Path: Default Codex home path.
    """
    home_path: Path = Path.home() / ".codex"
    return home_path


def _has_native_agent_toml_contract(codex_home: Path) -> bool:
    """Detect installed Codex native-agent TOML contract evidence.

    Args:
        codex_home [Path]: Codex home path to inspect.

    Returns:
        bool: ``True`` when at least one agent TOML matches required markers.
    """
    agents_dir: Path = codex_home / "agents"
    for agent_path in sorted(agents_dir.glob("*.toml")):
        text: str = agent_path.read_text(encoding="utf-8")
        if all(marker in text for marker in _REQUIRED_AGENT_TOML_MARKERS):
            supported: bool = True
            return supported

    supported = False
    return supported


def detect_codex_agent_capabilities(
    codex_home: str | Path | None = None,
    codex_version: str | None = None,
) -> CodexAgentCapabilitySnapshot:
    """Detect Codex-native agent materialization capabilities.

    Args:
        codex_home [str | Path | None]: Optional Codex home override.
        codex_version [str | None]: Optional externally probed Codex version.

    Returns:
        CodexAgentCapabilitySnapshot: Capability evidence.
    """
    resolved_codex_home: Path = (
        _default_codex_home() if codex_home is None else Path(codex_home)
    )
    native_agent_toml_supported: bool = _has_native_agent_toml_contract(
        resolved_codex_home
    )
    if native_agent_toml_supported:
        targets: tuple[str, ...] = ("project_codex_agents_toml",)
        warnings: tuple[str, ...] = ()
    else:
        targets = ()
        warnings = (
            f"No Codex native agent TOML contract was detected under {resolved_codex_home / 'agents'}.",
        )
    capability = CodexAgentCapabilitySnapshot(
        codex_home=str(resolved_codex_home),
        codex_version=codex_version,
        native_agent_toml_supported=native_agent_toml_supported,
        supported_materialization_targets=targets,
        warnings=warnings,
    )
    return capability
