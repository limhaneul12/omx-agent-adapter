from pathlib import Path

import pytest
from pydantic import ValidationError

from omx_remote.runtime.commands.command_catalog_resolver import load_command_catalog
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
    build_one_off_prompt_recipe,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)

NEW_COMMAND_IDS = {
    "collaboration-kickoff",
    "team-standup-sync",
    "integration-room",
    "conflict-resolution-council",
    "parallel-review-board",
    "release-readiness-room",
    "idea-to-prd-council",
}

EXPECTED_NEW_COMMAND_RISKS = {
    "collaboration-kickoff": CommandRisk.LONG_RUNNING,
    "team-standup-sync": CommandRisk.READ_ONLY,
    "integration-room": CommandRisk.LONG_RUNNING,
    "conflict-resolution-council": CommandRisk.LONG_RUNNING,
    "parallel-review-board": CommandRisk.LONG_RUNNING,
    "release-readiness-room": CommandRisk.WRITES_FILES,
    "idea-to-prd-council": CommandRisk.LONG_RUNNING,
}


def _write_agent_config(workspace: Path, agent_ids: tuple[str, ...]) -> None:
    agent_blocks = [
        f"""
[agents.{agent_id}]
enabled = true
provider = "codex"
role = "{agent_id}"
model = "gpt-5.5"
effort = "high"
persona = "Test {agent_id} persona."
""".strip()
        for agent_id in agent_ids
    ]
    (workspace / ".agent-remote.toml").write_text(
        "\n\n".join(agent_blocks), encoding="utf-8"
    )


def test_builtin_review_diff_dry_run_plan_is_inspectable(tmp_path: Path) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:review-diff")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.command_id == "review-diff"
    assert plan.source == CommandSource.BUILTIN
    assert plan.dry_run is True
    assert plan.steps[0].command == CommandStepCommand.CODEX_EXEC
    assert plan.steps[0].native_argv[:3] == ("codex", "exec", "--json")
    assert plan.steps[0].inline_prompt is not None
    assert plan.blocked_reasons == ()


def test_builtin_codex_deep_research_plan_includes_search_and_sandbox(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:codex-deep-research")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.EXTERNAL_NETWORK
    assert plan.steps[0].codex_search is True
    assert plan.steps[0].codex_sandbox == "read-only"
    assert plan.steps[0].native_argv[:6] == (
        "codex",
        "--search",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
    )
    assert "--search" in plan.steps[0].native_argv
    assert "--sandbox" in plan.steps[0].native_argv
    assert "read-only" in plan.steps[0].native_argv
    assert plan.blocked_reasons == ()


def test_builtin_research_interview_prd_plan_declares_artifacts(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:research-interview-prd")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.LONG_RUNNING
    assert len(plan.steps) == 6
    assert plan.steps[0].codex_search is True
    assert plan.steps[2].command == CommandStepCommand.PROMPT_ONLY
    assert str(tmp_path / ".agent-remote/runs/research-interview-prd/prd.md") in (
        plan.steps[-1].expected_artifacts
    )
    assert plan.blocked_reasons == ()


def test_builtin_alexandria_memory_capture_plan_targets_vault(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:alexandria-memory-capture")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.risk == CommandRisk.WRITES_FILES
    assert plan.steps[0].command == CommandStepCommand.PROMPT_ONLY
    assert plan.steps[0].expected_artifacts == (
        "/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/<descriptive-title>.md",
    )
    assert plan.blocked_reasons == ()


@pytest.mark.parametrize("command_id", sorted(NEW_COMMAND_IDS))
def test_new_builtin_command_dry_run_plan_is_inspectable(
    tmp_path: Path, command_id: str
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find(f"builtin:{command_id}")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="smoke task"
    )

    assert plan.command_id == command_id
    assert plan.qualified_id == f"builtin:{command_id}"
    assert plan.source == CommandSource.BUILTIN
    assert plan.dry_run is True
    assert plan.risk == EXPECTED_NEW_COMMAND_RISKS[command_id]
    assert plan.steps


def test_team_standup_sync_dry_run_uses_only_read_only_team_inspection(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:team-standup-sync")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    argv_text = "\n".join(" ".join(step.native_argv) for step in plan.steps)
    assert "agent-remote team status --team" in argv_text
    assert "agent-remote team tasks --team" in argv_text
    assert "agent-remote team events --team" in argv_text
    forbidden_terms = (" send ", " dispatch ", " claim ", " complete ", " launch ")
    assert not any(term in f" {argv_text} " for term in forbidden_terms)


def test_collaboration_kickoff_dry_run_includes_route_evidence_and_handoff(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:collaboration-kickoff")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="coordinate work"
    )

    argv_text = "\n".join(" ".join(step.native_argv) for step in plan.steps)
    assert "agent-remote cockpit snapshot" in argv_text
    assert "agent-remote next" in argv_text
    assert "agent-remote route recommend" in argv_text
    assert any(step.codex_sandbox == "read-only" for step in plan.steps)
    assert plan.steps[-1].command == CommandStepCommand.OMX_TEAM
    assert plan.steps[-1].role_lanes[0].execution == "runtime_handoff"
    assert not any(
        step.command == CommandStepCommand.OMX_ULTRAGOAL for step in plan.steps
    )


def test_collaboration_kickoff_codex_roles_are_agent_bound(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:collaboration-kickoff")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="coordinate work"
    )

    agent_bound_steps = tuple(
        step
        for step in plan.steps
        if any(lane.execution == "codex_subagent" for lane in step.role_lanes)
    )
    assert agent_bound_steps
    for step in agent_bound_steps:
        assert step.agent is not None
        assert "-c" in step.native_argv
        assert f'agent_type="{step.agent}"' in step.native_argv
    assert any(
        reason.startswith("No agent named researcher") for reason in plan.blocked_reasons
    )


def test_idea_to_prd_council_dry_run_includes_required_gates(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:idea-to-prd-council")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="information advantage radar"
    )

    plan_text = "\n".join(
        "\n".join((step.inline_prompt or "", *step.expected_artifacts))
        for step in plan.steps
    )
    argv_text = "\n".join("\n".join(step.native_argv) for step in plan.steps)
    assert "Alexandria intake" in plan_text
    assert "Alexandria closeout" in plan_text
    assert "Do not create, modify, or delete files directly" in argv_text
    assert sum(1 for step in plan.steps if step.codex_search) >= 2
    gap_steps = tuple(
        step
        for step in plan.steps
        if any(
            argv_part.endswith("/02_research/gap_research.md")
            for argv_part in step.native_argv
        )
    )
    assert len(gap_steps) == 1
    assert gap_steps[0].codex_search is False
    assert "do not run more live web research" in (gap_steps[0].inline_prompt or "")
    assert "approved_for_ultragoal" in plan_text
    validation_steps = tuple(
        step
        for step in plan.steps
        if any(
            argv_part.endswith("/05_validation/validation_verdict.md")
            for argv_part in step.native_argv
        )
    )
    assert len(validation_steps) == 1
    assert validation_steps[0].command == CommandStepCommand.LOCAL
    assert validation_steps[0].agent is None
    assert "Approve PRD handoff readiness only" in (
        validation_steps[0].inline_prompt or ""
    )
    closeout_steps = tuple(
        step
        for step in plan.steps
        if any(
            argv_part.endswith("/current/07_closeout/closeout.md")
            for argv_part in step.native_argv
        )
    )
    assert len(closeout_steps) == 1
    assert closeout_steps[0].command == CommandStepCommand.LOCAL
    assert closeout_steps[0].prompt_file is None
    assert "summary-only Alexandria closeout" in (
        closeout_steps[0].inline_prompt or ""
    )
    assert plan.steps[-1].command == CommandStepCommand.OMX_ULTRAGOAL
    assert plan.steps[-1].prompt_file is not None
    assert plan.steps[-1].prompt_file.endswith(
        "/current/06_ultragoal/ultragoal_brief.md"
    )
    assert "Roles: librarian" not in plan_text


def test_idea_to_prd_council_codex_roles_are_agent_bound(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:idea-to-prd-council")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="information advantage radar"
    )

    agent_bound_steps = tuple(
        step
        for step in plan.steps
        if any(lane.execution == "codex_subagent" for lane in step.role_lanes)
    )
    assert len(agent_bound_steps) >= 10
    for step in agent_bound_steps:
        assert step.agent is not None
        assert "-c" in step.native_argv
        assert f'agent_type="{step.agent}"' in step.native_argv
    assert any(
        reason.startswith("No agent named planner") for reason in plan.blocked_reasons
    )


def test_builtin_native_agents_are_unblocked_when_configured(
    tmp_path: Path,
) -> None:
    _write_agent_config(
        tmp_path,
        (
            "architect",
            "critic",
            "planner",
            "researcher",
            "team-executor",
            "test-engineer",
            "verifier",
            "writer",
        ),
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:idea-to-prd-council")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="information advantage radar"
    )

    assert not any(
        reason.startswith("No agent named") for reason in plan.blocked_reasons
    )


def test_release_readiness_room_dry_run_includes_closeout_phases(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("builtin:release-readiness-room")
    assert recipe is not None

    plan = build_command_execution_plan(
        recipe, cwd=tmp_path, dry_run=True, task_text="release suite"
    )

    plan_text = "\n".join(step.inline_prompt or "" for step in plan.steps)
    for term in (
        "verification_results",
        "review_board_verdict",
        "docs_verdict",
        "run_ledger_evidence",
        "Alexandria closeout",
        "approve_block_verdict",
        "blockers",
    ):
        assert term in plan_text


def test_new_builtin_commands_do_not_silently_launch_team_or_ultragoal_runtime(
    tmp_path: Path,
) -> None:
    catalog = load_command_catalog(cwd=tmp_path)

    for command_id in sorted(NEW_COMMAND_IDS - {"idea-to-prd-council", "collaboration-kickoff"}):
        recipe = catalog.find(f"builtin:{command_id}")
        assert recipe is not None
        plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)
        assert not any(
            step.command == CommandStepCommand.OMX_TEAM for step in plan.steps
        )
        assert not any(
            step.command == CommandStepCommand.OMX_ULTRAGOAL for step in plan.steps
        )

    collaboration = catalog.find("builtin:collaboration-kickoff")
    assert collaboration is not None
    collaboration_plan = build_command_execution_plan(
        collaboration, cwd=tmp_path, dry_run=True
    )
    assert collaboration_plan.steps[-1].command == CommandStepCommand.OMX_TEAM
    assert collaboration_plan.steps[-1].role_lanes[0].execution == "runtime_handoff"

    idea = catalog.find("builtin:idea-to-prd-council")
    assert idea is not None
    idea_plan = build_command_execution_plan(idea, cwd=tmp_path, dry_run=True)
    runtime_steps = tuple(
        step
        for step in idea_plan.steps
        if step.command
        in {CommandStepCommand.OMX_TEAM, CommandStepCommand.OMX_ULTRAGOAL}
    )
    assert len(runtime_steps) == 1
    assert runtime_steps[0].command == CommandStepCommand.OMX_ULTRAGOAL
    assert runtime_steps[0].index == len(idea_plan.steps)


def test_prompt_file_plan_reports_hash_and_native_argv(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompts" / "review.md"
    prompt_path.parent.mkdir()
    prompt_path.write_text("Review the diff.")
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/review.md"
output_last_message = ".agent-remote/runs/review/final-message.md"
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].prompt_file == str(prompt_path)
    assert plan.steps[0].prompt_exists is True
    assert plan.steps[0].prompt_sha256 is not None
    assert plan.steps[0].codex_sandbox == "read-only"
    assert "--sandbox" in plan.steps[0].native_argv
    assert "--output-last-message" in plan.steps[0].native_argv
    assert (
        str(tmp_path / ".agent-remote/runs/review/final-message.md")
        in plan.steps[0].expected_artifacts
    )


def test_codex_step_without_sandbox_defaults_to_read_only(tmp_path: Path) -> None:
    recipe = CommandRecipe(
        id="default-sandbox",
        source=CommandSource.REPO,
        description="Default Codex sandbox.",
        steps=(
            CommandStep(
                command=CommandStepCommand.CODEX_EXEC,
                inline_prompt="Review safely.",
            ),
        ),
    )

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].codex_sandbox == "read-only"
    assert plan.steps[0].native_argv[:5] == (
        "codex",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
    )


def test_missing_prompt_file_blocks_plan(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
provider = "codex"
mode = "exec"
prompt_file = "prompts/missing.md"
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].prompt_exists is False
    assert "Prompt file does not exist" in plan.steps[0].blocked_reasons[0]
    assert plan.blocked_reasons == plan.steps[0].blocked_reasons


def test_missing_agent_reference_blocks_plan(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.codex_review]
description = "Review current diff."
agent = "reviewer"
provider = "codex"
mode = "exec"
inline_prompt = "Review."
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert "No agent named reviewer" in plan.steps[0].blocked_reasons[0]


def test_configured_agent_reference_adds_codex_agent_type_override(
    tmp_path: Path,
) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[agents.reviewer]
enabled = true
provider = "codex"
role = "code-reviewer"
model = "gpt-5.5"
effort = "high"
persona = "Review the current diff."

[commands.codex_review]
description = "Review current diff."
agent = "reviewer"
provider = "codex"
mode = "exec"
inline_prompt = "Review."
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:codex_review")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.blocked_reasons == ()
    assert plan.steps[0].agent == "reviewer"
    assert plan.steps[0].native_argv[:3] == (
        "codex",
        "-c",
        'agent_type="reviewer"',
    )


def test_mcp_tool_plan_renders_comx_agent_call(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.read_state]
description = "Read active state through MCP."
provider = "mcp"
mode = "tool"
mcp_server = "local_state"
mcp_tool = "state_list_active"
mcp_arguments = { mode = "state" }
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:read_state")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].command == CommandStepCommand.MCP_TOOL
    assert plan.steps[0].native_argv == (
        "comx-agent",
        "mcp",
        "call",
        "local_state",
        "state_list_active",
    )
    assert plan.steps[0].mcp_arguments == {"mode": "state"}
    assert plan.blocked_reasons == ()


def test_repo_codex_step_supports_search_and_sandbox(tmp_path: Path) -> None:
    (tmp_path / ".agent-remote.toml").write_text(
        """
[commands.research]
description = "Research current docs."
provider = "codex"
mode = "exec"
codex_search = true
codex_sandbox = "read-only"
inline_prompt = "Research with citations."
""".strip()
    )
    catalog = load_command_catalog(cwd=tmp_path)
    recipe = catalog.find("repo:research")
    assert recipe is not None

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.steps[0].native_argv[:6] == (
        "codex",
        "--search",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
    )


def test_invalid_codex_sandbox_mode_is_rejected() -> None:
    with pytest.raises(ValidationError, match="codex_sandbox"):
        CommandStep(
            command=CommandStepCommand.CODEX_EXEC,
            codex_sandbox="invalid-mode",
        )


def test_codex_options_on_non_codex_step_are_rejected() -> None:
    with pytest.raises(ValidationError, match="command=codex_exec"):
        CommandStep(
            command=CommandStepCommand.LOCAL,
            argv=("echo", "hi"),
            codex_search=True,
        )


def test_incomplete_mcp_tool_plan_reports_blockers(tmp_path: Path) -> None:
    recipe = CommandRecipe(
        id="bad-mcp",
        source=CommandSource.REPO,
        description="Bad MCP recipe.",
        steps=(CommandStep(command=CommandStepCommand.MCP_TOOL),),
    )

    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert "MCP tool step requires mcp_server." in plan.blocked_reasons
    assert "MCP tool step requires mcp_tool." in plan.blocked_reasons


def test_one_off_prompt_recipe_uses_prompt_file(tmp_path: Path) -> None:
    prompt_path = tmp_path / "task.md"
    prompt_path.write_text("Do the task.")

    recipe = build_one_off_prompt_recipe(
        provider="codex",
        prompt_file=prompt_path,
        inline_prompt=None,
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=True)

    assert plan.command_id == "one-off-prompt"
    assert plan.risk == CommandRisk.READ_ONLY
    assert plan.steps[0].prompt_file == str(prompt_path)
    assert plan.steps[0].prompt_exists is True
