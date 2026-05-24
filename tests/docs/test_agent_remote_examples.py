from __future__ import annotations

import re
from pathlib import Path

import orjson

from omx_remote.runtime.agents.agent_config_loader import load_agent_config


EXAMPLE_DOCS = (
    Path("docs/examples/agent-remote-command-recipes.md"),
    Path("docs/examples/agent-remote-route-recommendations.md"),
    Path("docs/examples/agent-remote-run-records.md"),
    Path("docs/examples/agent-remote-subagents-toml.md"),
    Path("docs/examples/agent-remote-ultragoal.md"),
)


def _json_blocks(markdown_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"```json\n(.*?)\n```", markdown_text, flags=re.DOTALL))


def _toml_blocks(markdown_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"```toml\n(.*?)\n```", markdown_text, flags=re.DOTALL))


def test_agent_remote_example_docs_exist_and_have_valid_json_blocks() -> None:
    for doc_path in EXAMPLE_DOCS:
        markdown_text = doc_path.read_text(encoding="utf-8")
        json_blocks = _json_blocks(markdown_text)

        assert json_blocks, f"{doc_path} should include at least one JSON example"
        for json_block in json_blocks:
            orjson.loads(json_block)


def test_readme_surfaces_command_composition_flow() -> None:
    readme_text = Path("README.md").read_text(encoding="utf-8")

    expected_commands = (
        "agent-remote agents validate --cwd .",
        "agent-remote cockpit snapshot --cwd .",
        "agent-remote route recommend --task",
        "agent-remote run review-diff --cwd . --dry-run",
        "agent-remote runs handoff",
        "agent-remote probes run omx-basic",
        "agent-remote agents plan-apply-codex --cwd .",
        "agent-remote ultragoal status --cwd .",
    )
    for expected_command in expected_commands:
        assert expected_command in readme_text

    assert "agent-remote hypergoal" not in readme_text.lower()


def test_subagent_toml_example_matches_loader_contract(tmp_path: Path) -> None:
    markdown_text = Path("docs/examples/agent-remote-subagents-toml.md").read_text(
        encoding="utf-8"
    )
    toml_blocks = _toml_blocks(markdown_text)

    assert toml_blocks
    (tmp_path / ".agent-remote.toml").write_text(toml_blocks[0], encoding="utf-8")
    config = load_agent_config(cwd=tmp_path)

    assert [agent.id for agent in config.agents] == ["reviewer"]
