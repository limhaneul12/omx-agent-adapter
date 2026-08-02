from __future__ import annotations

import re
from pathlib import Path

from comx_harness.ade.codex_subagent_config import update_project_config
from comx_harness.ade.codex_subagent_toml import (
    atomic_write_project_file,
    ensure_project_codex_directories,
    parse_toml,
    read_toml_file,
    relative_agent_config_file,
    render_agent_file,
)
from comx_harness.schemas.codex_subagent_schemas import (
    CodexRegisteredSubagentState,
    CodexSubagentFileConfig,
    CodexSubagentPlannedFile,
    CodexSubagentRegistrationReport,
    CodexSubagentRegistrationSpec,
    CodexSubagentRegistryState,
    CodexSubagentValidationReport,
)
from pydantic import ValidationError

_CONFIG_FILE_NAME = "config.toml"
_AGENTS_DIRECTORY_NAME = "agents"
_MAX_THREADS_KEY = "max_concurrent_threads_per_session"
_LEGACY_MAX_THREADS_KEY = "max_threads"
_SAFE_AGENT_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_RESERVED_AGENT_SETTINGS = frozenset(
    {
        _MAX_THREADS_KEY,
        _LEGACY_MAX_THREADS_KEY,
        "default_subagent_model",
        "default_subagent_reasoning_effort",
        "enabled",
        "interrupt_message",
    }
)


class CodexSubagentRegistry:
    """Validate and materialize project-local Codex custom-agent config."""

    def validate(
        self,
        workspace: Path,
        spec: CodexSubagentRegistrationSpec,
    ) -> CodexSubagentValidationReport:
        workspace_root, codex_root, agents_root = _project_paths(workspace)
        config_path = codex_root / _CONFIG_FILE_NAME
        _validate_existing_project_paths(codex_root, agents_root, config_path)
        current_config = (
            config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        )
        prospective_config = update_project_config(current_config, spec)
        parse_toml(prospective_config, config_path)

        warnings: list[str] = []
        planned_files: list[CodexSubagentPlannedFile] = []
        for agent in spec.agents:
            destination = _agent_path(agents_root, codex_root, agent.name)
            if destination.exists():
                warnings.append(f"Registration would update {destination}.")
            planned_files.append(
                CodexSubagentPlannedFile(
                    name=agent.name,
                    config_file=relative_agent_config_file(agent.name),
                    destination=str(destination),
                )
            )

        report = CodexSubagentValidationReport(
            workspace=str(workspace_root),
            config_path=str(config_path),
            max_concurrent_threads_per_session=(
                spec.max_concurrent_threads_per_session
            ),
            agents=tuple(planned_files),
            warnings=tuple(warnings),
        )
        return report

    def register(
        self,
        workspace: Path,
        spec: CodexSubagentRegistrationSpec,
    ) -> CodexSubagentRegistrationReport:
        validation = self.validate(workspace, spec)
        workspace_root = Path(validation.workspace)
        codex_root = workspace_root / ".codex"
        agents_root = codex_root / _AGENTS_DIRECTORY_NAME
        config_path = codex_root / _CONFIG_FILE_NAME

        ensure_project_codex_directories(workspace_root)
        _validate_existing_project_paths(codex_root, agents_root, config_path)

        current_config = (
            config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        )
        updated_config = update_project_config(current_config, spec)
        parse_toml(updated_config, config_path)

        written_files: list[str] = []
        for agent in spec.agents:
            destination = _agent_path(agents_root, codex_root, agent.name)
            atomic_write_project_file(
                workspace_root,
                Path(".codex") / "agents" / destination.name,
                render_agent_file(agent),
            )
            written_files.append(str(destination))
        atomic_write_project_file(
            workspace_root,
            Path(".codex") / _CONFIG_FILE_NAME,
            updated_config,
        )
        written_files.append(str(config_path))

        registry = self.list(workspace_root)
        report = CodexSubagentRegistrationReport(
            workspace=str(workspace_root),
            config_path=str(config_path),
            written_files=tuple(written_files),
            registry=registry,
        )
        return report

    def list(self, workspace: Path) -> CodexSubagentRegistryState:
        workspace_root, codex_root, agents_root = _project_paths(workspace)
        config_path = codex_root / _CONFIG_FILE_NAME
        _validate_existing_project_paths(codex_root, agents_root, config_path)

        warnings: list[str] = []
        registry_valid = True
        config = read_toml_file(config_path)
        agents_config = _agents_config(config)
        max_threads, max_threads_valid = _read_max_threads(agents_config, warnings)
        registry_valid = registry_valid and max_threads_valid

        registered_agents: list[CodexRegisteredSubagentState] = []
        registered_files: set[str] = set()
        for name in sorted(agents_config):
            raw_registration = agents_config[name]
            if not isinstance(raw_registration, dict):
                if name not in _RESERVED_AGENT_SETTINGS:
                    registry_valid = False
                    warnings.append(
                        f"{name}: custom Codex agent registration must be a TOML table."
                    )
                continue
            state = _read_registered_agent(
                name=name,
                raw_registration=raw_registration,
                codex_root=codex_root,
                agents_root=agents_root,
            )
            registered_agents.append(state)
            registry_valid = registry_valid and state.valid
            if state.config_file is not None:
                registered_files.add(state.config_file)
            warnings.extend(f"{name}: {warning}" for warning in state.warnings)

        if not config_path.exists():
            warnings.append(f"No project Codex config found at {config_path}.")

        if agents_root.exists():
            for agent_file in sorted(agents_root.glob("*.toml")):
                relative_file = f"agents/{agent_file.name}"
                if agent_file.is_symlink():
                    registry_valid = False
                    warnings.append(
                        f"Refusing symlinked Codex agent file {agent_file}."
                    )
                elif relative_file not in registered_files:
                    warnings.append(
                        f"Unregistered Codex agent file found at {agent_file}."
                    )

        state = CodexSubagentRegistryState(
            workspace=str(workspace_root),
            config_path=str(config_path),
            config_exists=config_path.is_file(),
            max_concurrent_threads_per_session=max_threads,
            agents=tuple(registered_agents),
            warnings=tuple(warnings),
            valid=registry_valid,
        )
        return state


def _project_paths(workspace: Path) -> tuple[Path, Path, Path]:
    workspace_root = workspace.expanduser().resolve()
    user_home = Path.home().resolve()
    user_codex_root = (user_home / ".codex").resolve(strict=False)
    if workspace_root == user_home:
        raise ValueError("User home cannot be used as a Codex registration workspace")
    if workspace_root == user_codex_root or workspace_root.is_relative_to(
        user_codex_root
    ):
        raise ValueError(
            "Workspace cannot be inside the user-global Codex directory ~/.codex"
        )
    if not workspace_root.exists():
        raise FileNotFoundError(f"Workspace does not exist: {workspace_root}")
    if not workspace_root.is_dir():
        raise NotADirectoryError(f"Workspace is not a directory: {workspace_root}")
    codex_root = workspace_root / ".codex"
    agents_root = codex_root / _AGENTS_DIRECTORY_NAME
    return workspace_root, codex_root, agents_root


def _validate_existing_project_paths(
    codex_root: Path,
    agents_root: Path,
    config_path: Path,
) -> None:
    for directory in (codex_root, agents_root):
        if directory.is_symlink():
            raise ValueError(f"Refusing symlinked project Codex directory: {directory}")
        if directory.exists() and not directory.is_dir():
            raise NotADirectoryError(f"Expected directory at {directory}")
    if config_path.is_symlink():
        raise ValueError(f"Refusing symlinked project Codex config: {config_path}")
    if config_path.exists() and not config_path.is_file():
        raise ValueError(f"Expected regular file at {config_path}")


def _agent_path(agents_root: Path, codex_root: Path, name: str) -> Path:
    destination = agents_root / f"{name}.toml"
    if destination.is_symlink():
        raise ValueError(f"Refusing symlinked Codex agent file: {destination}")
    resolved_destination = destination.resolve(strict=False)
    resolved_codex_root = codex_root.resolve(strict=False)
    if not resolved_destination.is_relative_to(resolved_codex_root):
        raise ValueError(f"Codex agent path escapes project .codex: {destination}")
    return destination


def _agents_config(config: dict[str, object]) -> dict[str, object]:
    raw_agents = config.get("agents", {})
    if raw_agents == {}:
        return {}
    if not isinstance(raw_agents, dict):
        raise ValueError("Codex config agents value must be a TOML table")
    return raw_agents


def _read_max_threads(
    agents_config: dict[str, object],
    warnings: list[str],
) -> tuple[int | None, bool]:
    raw_max_threads = agents_config.get(_MAX_THREADS_KEY)
    if raw_max_threads is None:
        raw_max_threads = agents_config.get(_LEGACY_MAX_THREADS_KEY)
        if raw_max_threads is not None:
            warnings.append(
                "Codex config uses legacy agents.max_threads; prefer "
                "agents.max_concurrent_threads_per_session."
            )
    if raw_max_threads is None:
        return None, True
    if (
        isinstance(raw_max_threads, bool)
        or not isinstance(raw_max_threads, int)
        or not 1 <= raw_max_threads <= 64
    ):
        warnings.append(
            "agents.max_concurrent_threads_per_session must be an integer from 1 to 64."
        )
        return None, False
    return raw_max_threads, True


def _read_registered_agent(
    *,
    name: str,
    raw_registration: dict[object, object],
    codex_root: Path,
    agents_root: Path,
) -> CodexRegisteredSubagentState:
    warnings: list[str] = []
    name_is_safe = _SAFE_AGENT_NAME.fullmatch(name) is not None
    if not name_is_safe:
        warnings.append("registration name is not a safe project-local agent name")
    description_value = raw_registration.get("description")
    config_file_value = raw_registration.get("config_file")
    description = description_value if isinstance(description_value, str) else None
    config_file = config_file_value if isinstance(config_file_value, str) else None
    if description is None or not description.strip():
        warnings.append("registration description is missing or blank")
        description = None
    if config_file is None:
        warnings.append("registration config_file is missing")

    file_config: CodexSubagentFileConfig | None = None
    file_exists = False
    if config_file is not None and name_is_safe:
        expected_file = relative_agent_config_file(name)
        if config_file != expected_file:
            warnings.append(
                f"config_file must be deterministic project path {expected_file!r}"
            )
        else:
            agent_path = _agent_path(agents_root, codex_root, name)
            file_exists = agent_path.is_file()
            if not file_exists:
                warnings.append(f"registered agent file is missing at {agent_path}")
            else:
                try:
                    file_config = CodexSubagentFileConfig.model_validate(
                        read_toml_file(agent_path)
                    )
                except (ValidationError, ValueError) as error:
                    warnings.append(f"invalid agent TOML: {error}")

    state = CodexRegisteredSubagentState(
        name=name,
        description=description,
        config_file=config_file,
        file_exists=file_exists,
        valid=not warnings,
        model=file_config.model if file_config is not None else None,
        model_reasoning_effort=(
            file_config.model_reasoning_effort if file_config is not None else None
        ),
        sandbox_mode=file_config.sandbox_mode if file_config is not None else None,
        developer_instructions=(
            file_config.developer_instructions if file_config is not None else None
        ),
        warnings=tuple(warnings),
    )
    return state
