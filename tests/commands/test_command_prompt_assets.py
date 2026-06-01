import re
from pathlib import Path

import orjson

from omx_remote.runtime.commands.catalog.builtin_command_catalog import (
    build_builtin_command_catalog,
)
from omx_remote.runtime.prompt_assets import prompt_asset_path
from omx_remote.runtime.commands.planning.command_step_planner import (
    build_command_execution_plan,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandStepCommand
from omx_remote.schemas.discovery_gate_schemas import DiscoveryGateResult

PROMPT_HEAVY_COMMANDS = {
    "route-next": ("<task>",),
    "discovery-gate": (
        "<task>",
        "Discovery Decision Packet",
        "run-deep-interview",
        "no-build",
        "company-run suitability",
        "Alexandria MCP",
        "non-goals",
        "decision boundaries",
    ),
    "research-brief": ("<task>",),
    "idea-to-prd": ("<task>",),
    "implementation-kickoff": ("<task>",),
    "team-sync": ("<task>",),
    "integration-plan": ("<task>",),
    "review-gate": ("<task>",),
    "release-readiness": ("<task>",),
    "company-run": (
        "<task>",
        "discovery-gate",
        "user-facing decision report",
        "Alexandria MCP",
    ),
    "adapter-ops mcp-audit": ("<task>",),
    "adapter-ops contract-refresh": ("<task>",),
    "adapter-ops skillize": ("<task>",),
    "adapter-ops run-ledger": ("<task>",),
    "adapter-ops memory-capture": ("Alexandria MCP",),
}


def test_prompt_asset_path_resolves_repo_root_prompt_directory() -> None:
    path = Path(prompt_asset_path("company-run", "company-run-orchestration.md"))

    assert path.is_absolute()
    assert path.parts[-3:] == ("prompt", "company-run", "company-run-orchestration.md")
    assert path.exists()


def test_builtin_prompt_assets_exist_and_include_required_terms() -> None:
    catalog = build_builtin_command_catalog()

    for command_id, required_terms in PROMPT_HEAVY_COMMANDS.items():
        recipe = catalog.find(f"builtin:{command_id}")
        assert recipe is not None
        prompt_files = tuple(
            Path(step.prompt_file)
            for step in recipe.steps
            if step.prompt_file is not None
        )
        assert prompt_files, f"{command_id} should use repo-root prompt assets"
        for prompt_file in prompt_files:
            assert prompt_file.exists(), f"missing prompt asset: {prompt_file}"
            prompt_text = prompt_file.read_text(encoding="utf-8")
            assert "EOF'" not in prompt_text
            assert "\nEOF\n" not in prompt_text
            for term in required_terms:
                assert term in prompt_text


def test_prompt_assets_are_reported_in_dry_run_metadata(tmp_path: Path) -> None:
    catalog = build_builtin_command_catalog()
    recipe = catalog.find("builtin:company-run")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="company idea"
    )

    prompt_steps = tuple(
        step
        for step in plan.steps
        if step.command == CommandStepCommand.CODEX_EXEC
        and step.prompt_file is not None
    )
    assert prompt_steps
    assert all(step.prompt_exists is True for step in prompt_steps)
    assert all(step.prompt_sha256 is not None for step in prompt_steps)
    assert any(
        "/prompt/company-run/company-run-orchestration.md" in step.prompt_file
        for step in prompt_steps
    )


def test_discovery_gate_prompt_packet_example_matches_schema() -> None:
    prompt_path = Path(prompt_asset_path("discovery-gate", "discovery-gate.md"))
    prompt_text = prompt_path.read_text(encoding="utf-8")
    match = re.search(
        r"The JSON object must include every field below.*?```json\n(?P<payload>.*?)\n```",
        prompt_text,
        flags=re.DOTALL,
    )

    assert match is not None
    payload = orjson.loads(match.group("payload"))
    result = DiscoveryGateResult.model_validate(payload)
    catalog = build_builtin_command_catalog()
    recipe = catalog.find("builtin:discovery-gate")
    assert recipe is not None
    declared_artifacts = set(recipe.steps[0].expected_artifacts)

    assert result.verdict == "ready-for-company-run"
    assert declared_artifacts.issubset(set(result.artifacts))
