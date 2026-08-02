from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from comx_harness.ade.codex_subagent_registry import CodexSubagentRegistry
from comx_harness.schemas.codex_subagent_schemas import (
    CodexSubagentRegistrationSpec,
)
from comx_harness.schemas.execution_schemas import RunOptions
from comx_harness.shared.harness_enums.execution_enums import ReasoningEffort
from comx_harness.storage.json_file_store import read_json
from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).parents[3]
DOGFOOD_SPEC_PATH = (
    REPOSITORY_ROOT / "examples" / "codex-subagents" / "stock-informer.json"
)


def _dogfood_spec() -> CodexSubagentRegistrationSpec:
    spec = CodexSubagentRegistrationSpec.model_validate(read_json(DOGFOOD_SPEC_PATH))
    return spec


def test_dogfood_registration_spec_is_valid() -> None:
    spec = _dogfood_spec()

    assert spec.max_concurrent_threads_per_session == 5
    assert tuple(agent.name for agent in spec.agents) == (
        "luna_feature_auditor_max",
        "luna_test_analyst_max",
        "terra_integration_reviewer",
        "luna_docs_researcher_medium",
        "luna_bounded_worker_max",
    )
    assert spec.agents[0].model_reasoning_effort == "max"
    assert spec.agents[-1].sandbox_mode == "workspace-write"


def test_codex_subagent_max_effort_does_not_expand_run_options() -> None:
    assert tuple(ReasoningEffort) == (
        ReasoningEffort.LOW,
        ReasoningEffort.MEDIUM,
        ReasoningEffort.HIGH,
        ReasoningEffort.XHIGH,
    )

    with pytest.raises(ValidationError):
        RunOptions(reasoning_effort="max")


@pytest.mark.parametrize(
    "invalid_name",
    ("../escape", "nested/agent", ".hidden", "UpperCase", "agent.toml"),
)
def test_registration_spec_rejects_invalid_or_traversing_names(
    invalid_name: str,
) -> None:
    raw_spec = read_json(DOGFOOD_SPEC_PATH)
    raw_spec["agents"][0]["name"] = invalid_name

    with pytest.raises(ValidationError):
        CodexSubagentRegistrationSpec.model_validate(raw_spec)


@pytest.mark.parametrize("invalid_threads", (True, 5.0, "5"))
def test_registration_spec_rejects_coerced_thread_counts(
    invalid_threads: object,
) -> None:
    raw_spec = read_json(DOGFOOD_SPEC_PATH)
    raw_spec["max_concurrent_threads_per_session"] = invalid_threads

    with pytest.raises(ValidationError):
        CodexSubagentRegistrationSpec.model_validate(raw_spec)


def test_validate_is_read_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    report = CodexSubagentRegistry().validate(workspace, _dogfood_spec())

    assert report.valid is True
    assert report.mutation_performed is False
    assert not (workspace / ".codex").exists()


def test_validate_supports_existing_inline_registration_without_mutation(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    codex_root.mkdir(parents=True)
    (codex_root / "config.toml").write_text(
        'agents.luna_feature_auditor_max = { description = "Existing", '
        'config_file = "agents/luna_feature_auditor_max.toml" }\n',
        encoding="utf-8",
    )

    report = CodexSubagentRegistry().validate(workspace, _dogfood_spec())

    assert report.valid is True
    assert report.mutation_performed is False
    assert not (codex_root / "agents").exists()
    assert "Existing" in (codex_root / "config.toml").read_text(encoding="utf-8")


def test_register_writes_project_config_and_agent_files_then_lists_them(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    workspace.mkdir()
    codex_root.mkdir()
    (codex_root / "config.toml").write_text(
        'model = "existing-model"\n\n[features]\nmulti_agent = true\n',
        encoding="utf-8",
    )

    registry = CodexSubagentRegistry()
    report = registry.register(workspace, _dogfood_spec())
    state = registry.list(workspace)

    config = tomllib.loads((codex_root / "config.toml").read_text(encoding="utf-8"))
    assert config["model"] == "existing-model"
    assert config["features"]["multi_agent"] is True
    assert config["agents"]["max_concurrent_threads_per_session"] == 5
    assert config["agents"]["luna_feature_auditor_max"]["config_file"] == (
        "agents/luna_feature_auditor_max.toml"
    )
    assert len(report.written_files) == 6
    assert state.valid is True
    assert state.max_concurrent_threads_per_session == 5
    assert tuple(agent.name for agent in state.agents) == (
        "luna_bounded_worker_max",
        "luna_docs_researcher_medium",
        "luna_feature_auditor_max",
        "luna_test_analyst_max",
        "terra_integration_reviewer",
    )
    assert all(agent.file_exists and agent.valid for agent in state.agents)

    feature_auditor = tomllib.loads(
        (codex_root / "agents" / "luna_feature_auditor_max.toml").read_text(
            encoding="utf-8"
        )
    )
    assert feature_auditor == {
        "model": "gpt-5.6-luna",
        "model_reasoning_effort": "max",
        "sandbox_mode": "read-only",
        "developer_instructions": (
            "Review the requested feature against repository rules. Stay read-only "
            "and report concrete file evidence, risks, and missing verification."
        ),
    }


def test_register_updates_existing_requested_agent_without_duplicate_table(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    registry = CodexSubagentRegistry()
    spec = _dogfood_spec()

    registry.register(workspace, spec)
    registry.register(workspace, spec)

    config_text = (workspace / ".codex" / "config.toml").read_text(encoding="utf-8")
    tomllib.loads(config_text)
    assert config_text.count("[agents.luna_feature_auditor_max]") == 1


def test_register_updates_quoted_requested_agent_table(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    codex_root.mkdir(parents=True)
    (codex_root / "config.toml").write_text(
        '[agents."luna_feature_auditor_max"]\n'
        'description = "Stale description"\n'
        'config_file = "agents/luna_feature_auditor_max.toml"\n\n'
        "[features]\n"
        "multi_agent = true\n",
        encoding="utf-8",
    )

    CodexSubagentRegistry().register(workspace, _dogfood_spec())

    config_text = (codex_root / "config.toml").read_text(encoding="utf-8")
    config = tomllib.loads(config_text)
    assert config["features"]["multi_agent"] is True
    assert config["agents"]["luna_feature_auditor_max"]["description"] == (
        "Audit feature scope, repository fit, and implementation evidence."
    )


@pytest.mark.parametrize(
    "existing_max_threads",
    (
        "agents.max_threads = 2\n",
        '[agents]\n"max_concurrent_threads_per_session" = 2\n',
    ),
)
def test_register_normalizes_equivalent_max_thread_declarations(
    tmp_path: Path,
    existing_max_threads: str,
) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    codex_root.mkdir(parents=True)
    (codex_root / "config.toml").write_text(
        f"{existing_max_threads}\n[features]\nmulti_agent = true\n",
        encoding="utf-8",
    )

    CodexSubagentRegistry().register(workspace, _dogfood_spec())

    config = tomllib.loads((codex_root / "config.toml").read_text(encoding="utf-8"))
    assert config["features"]["multi_agent"] is True
    assert config["agents"]["max_concurrent_threads_per_session"] == 5
    assert "max_threads" not in config["agents"]


def test_register_refuses_symlinked_project_codex_directory(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / ".codex").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked project Codex directory"):
        CodexSubagentRegistry().register(workspace, _dogfood_spec())

    assert tuple(outside.iterdir()) == ()


def test_registry_rejects_user_home_and_alias_to_home(tmp_path: Path) -> None:
    registry = CodexSubagentRegistry()

    with pytest.raises(ValueError, match="User home"):
        registry.validate(Path.home(), _dogfood_spec())

    home_alias = tmp_path / "home-alias"
    home_alias.symlink_to(Path.home(), target_is_directory=True)
    with pytest.raises(ValueError, match="User home"):
        registry.validate(home_alias, _dogfood_spec())


def test_registry_rejects_user_global_codex_and_alias(tmp_path: Path) -> None:
    registry = CodexSubagentRegistry()
    user_codex = Path.home() / ".codex"

    with pytest.raises(ValueError, match="user-global Codex directory"):
        registry.validate(user_codex, _dogfood_spec())

    codex_alias = tmp_path / "codex-alias"
    codex_alias.symlink_to(user_codex, target_is_directory=True)
    with pytest.raises(ValueError, match="user-global Codex directory"):
        registry.validate(codex_alias, _dogfood_spec())


@pytest.mark.parametrize("target_kind", ("agents", "config", "agent"))
def test_register_refuses_symlinked_codex_targets(
    tmp_path: Path,
    target_kind: str,
) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    agents_root = codex_root / "agents"
    outside = tmp_path / "outside"
    agents_root.mkdir(parents=True)
    outside.mkdir()
    if target_kind == "agents":
        agents_root.rmdir()
        agents_root.symlink_to(outside, target_is_directory=True)
    elif target_kind == "config":
        (codex_root / "config.toml").symlink_to(outside / "config.toml")
    else:
        (agents_root / "luna_feature_auditor_max.toml").symlink_to(
            outside / "agent.toml"
        )

    with pytest.raises(ValueError, match="symlinked"):
        CodexSubagentRegistry().register(workspace, _dogfood_spec())

    assert tuple(outside.iterdir()) == ()


def test_list_reports_traversing_registration_without_reading_outside(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    codex_root.mkdir(parents=True)
    (codex_root / "config.toml").write_text(
        '[agents."../escape"]\n'
        'description = "Unsafe"\n'
        'config_file = "agents/../escape.toml"\n',
        encoding="utf-8",
    )
    outside_file = workspace / "escape.toml"
    outside_file.write_text('model = "must-not-be-read"\n', encoding="utf-8")

    state = CodexSubagentRegistry().list(workspace)

    assert state.valid is False
    assert state.agents[0].name == "../escape"
    assert state.agents[0].file_exists is False
    assert "safe project-local agent name" in state.agents[0].warnings[0]


def test_list_reports_unknown_scalar_agent_registration(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    codex_root = workspace / ".codex"
    codex_root.mkdir(parents=True)
    (codex_root / "config.toml").write_text(
        '[agents]\nreviewer = "not-a-table"\n',
        encoding="utf-8",
    )

    state = CodexSubagentRegistry().list(workspace)

    assert state.valid is False
    assert "must be a TOML table" in state.warnings[0]
