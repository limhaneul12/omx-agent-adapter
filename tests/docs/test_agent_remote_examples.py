from __future__ import annotations

import re
from pathlib import Path

import orjson


EXAMPLE_DOCS = (
    Path("docs/examples/agent-remote-command-recipes.md"),
    Path("docs/examples/agent-remote-route-recommendations.md"),
    Path("docs/examples/agent-remote-run-records.md"),
    Path("docs/examples/agent-remote-subagents-toml.md"),
    Path("docs/examples/agent-remote-ultragoal.md"),
)


def _json_blocks(markdown_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"```json\n(.*?)\n```", markdown_text, flags=re.DOTALL))


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
