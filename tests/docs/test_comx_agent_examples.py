from __future__ import annotations

import re
from pathlib import Path

import orjson

from omx_remote.runtime.agents.agent_config_loader import load_agent_config
EXAMPLE_DOCS = (
    Path("docs/examples/comx-agent-command-recipes.md"),
    Path("docs/examples/comx-agent-route-recommendations.md"),
    Path("docs/examples/comx-agent-run-records.md"),
    Path("docs/examples/comx-agent-subagents-toml.md"),
    Path("docs/examples/comx-agent-ultragoal.md"),
)

DOCS_WITH_LOCAL_LINKS = (
    Path("AGENTS.md"),
    Path("README.md"),
    *EXAMPLE_DOCS,
)


def _json_blocks(markdown_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"```json\n(.*?)\n```", markdown_text, flags=re.DOTALL))


def _toml_blocks(markdown_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"```toml\n(.*?)\n```", markdown_text, flags=re.DOTALL))


def _local_markdown_links(markdown_text: str) -> tuple[str, ...]:
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown_text)
    local_links = tuple(
        link
        for link in links
        if not link.startswith(("http://", "https://", "mailto:", "#"))
    )
    return local_links


def test_comx_agent_example_docs_exist_and_have_valid_json_blocks() -> None:
    for doc_path in EXAMPLE_DOCS:
        markdown_text = doc_path.read_text(encoding="utf-8")
        json_blocks = _json_blocks(markdown_text)

        assert json_blocks, f"{doc_path} should include at least one JSON example"
        for json_block in json_blocks:
            orjson.loads(json_block)


def test_readme_surfaces_command_composition_flow() -> None:
    readme_text = Path("README.md").read_text(encoding="utf-8")

    expected_commands = (
        "comx-agent agents validate --cwd .",
        "comx-agent cockpit snapshot --cwd .",
        "comx-agent route recommend --task",
        "comx-agent run builtin:review-gate --cwd . --dry-run",
        "comx-agent runs handoff",
        "comx-agent probes run omx-basic",
        "comx-agent agents plan-apply-codex --cwd .",
        "comx-agent ultragoal status --cwd .",
        "comx-agent run builtin:research-brief --cwd . --dry-run",
        "comx-agent run builtin:idea-to-prd --cwd . --dry-run",
        "comx-agent run builtin:implementation-kickoff --cwd . --dry-run",
        "comx-agent run builtin:company-run --cwd . --dry-run",
        "comx-agent run 'builtin:adapter-ops mcp-audit' --cwd . --dry-run",
    )
    for expected_command in expected_commands:
        assert expected_command in readme_text

    assert "comx-agent hypergoal" not in readme_text.lower()
    assert "exactly nine public workflow commands" in readme_text
    assert "company-run" in readme_text


def test_local_markdown_links_target_existing_files() -> None:
    for doc_path in DOCS_WITH_LOCAL_LINKS:
        markdown_text = doc_path.read_text(encoding="utf-8")
        for link in _local_markdown_links(markdown_text):
            path_text, _, _anchor = link.partition("#")
            if not path_text:
                continue
            target_path = (doc_path.parent / path_text).resolve()
            assert target_path.exists(), f"{doc_path} links missing file {link}"


def test_subagent_toml_example_matches_loader_contract(tmp_path: Path) -> None:
    markdown_text = Path("docs/examples/comx-agent-subagents-toml.md").read_text(
        encoding="utf-8"
    )
    toml_blocks = _toml_blocks(markdown_text)

    assert toml_blocks
    (tmp_path / ".comx-agent.toml").write_text(toml_blocks[0], encoding="utf-8")
    config = load_agent_config(cwd=tmp_path)

    assert [agent.id for agent in config.agents] == ["reviewer"]
