from omx_remote.runtime.commands.command_blueprint_helpers import (
    codex_step,
    local_step,
    prompt_step,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
)


def _verify_handoff_plus_recipe() -> CommandRecipe:
    """Implement verify handoff plus recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="verify-handoff-plus",
        source=CommandSource.BUILTIN,
        description=(
            "Run expanded verification gates, TUI/research smokes, and a final "
            "Codex review handoff summary."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("git", "diff", "--check")),
            local_step(("uv", "run", "ruff", "check", "src", "tests")),
            local_step(("uv", "run", "pyrefly", "check", "src")),
            local_step(("uv", "run", "pytest", "tests/commands", "tests/comx", "-q")),
            local_step(("uv", "run", "comx-agent", "tui", "--cwd", ".", "--once")),
            codex_step(
                "Review the current diff and verification evidence. Produce final "
                "handoff findings, risk assessment, and an approve/block recommendation.",
                output_last_message=".agent-remote/runs/verify-handoff-plus/handoff.md",
            ),
        ),
    )
    return recipe


def _route_doctor_recipe() -> CommandRecipe:
    """Implement route doctor recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="route-doctor",
        source=CommandSource.BUILTIN,
        description=(
            "Diagnose the safest Codex/OMX/project route for a task using catalog, "
            "route policy, preflight, runtime status, and next-action evidence."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("agent-remote", "commands", "list", "--cwd", ".", "--json")),
            local_step(
                (
                    "agent-remote",
                    "route",
                    "recommend",
                    "--task",
                    "<task>",
                    "--cwd",
                    ".",
                    "--json",
                )
            ),
            local_step(
                (
                    "agent-remote",
                    "preflight",
                    "route",
                    "<route>",
                    "--cwd",
                    ".",
                    "--json",
                )
            ),
            codex_step(
                "Synthesize a route-doctor report from command catalog, route policy, "
                "preflight, runtime status, and next-action evidence. Include recommended "
                "route, blocked alternatives, risk labels, and the next preview command.",
                output_last_message=".agent-remote/runs/route-doctor/report.md",
            ),
        ),
    )
    return recipe


def _mcp_onboard_audit_recipe() -> CommandRecipe:
    """Implement mcp onboard audit recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="mcp-onboard-audit",
        source=CommandSource.BUILTIN,
        description=(
            "Audit Codex and comx-agent MCP configuration, tool visibility, OAuth/env "
            "risks, redaction needs, and safe registration commands."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("codex", "mcp", "--help")),
            local_step(("comx-agent", "mcp", "servers", "--cwd", ".", "--json")),
            local_step(
                ("comx-agent", "mcp", "tools", "omx_agent", "--cwd", ".", "--json")
            ),
            codex_step(
                "Audit MCP onboarding evidence. Identify configured servers, missing "
                "omx_agent registration, env/header/OAuth secret risks, tool approval "
                "policy concerns, and safe dry-run registration commands.",
                output_last_message=".agent-remote/runs/mcp-onboard-audit/audit.md",
            ),
        ),
    )
    return recipe


def _upstream_contract_refresh_recipe() -> CommandRecipe:
    """Implement upstream contract refresh recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="upstream-contract-refresh",
        source=CommandSource.BUILTIN,
        description=(
            "Run Codex/OMX probe suites and compare captured fixtures so adapter "
            "support is grounded in current observed contracts."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(
                ("agent-remote", "probes", "run", "codex-basic", "--cwd", ".", "--json")
            ),
            local_step(
                ("agent-remote", "probes", "run", "omx-basic", "--cwd", ".", "--json")
            ),
            local_step(("agent-remote", "probes", "list-fixtures", "--json")),
            codex_step(
                "Compare current Codex/OMX probe results for: <task>. Compare with known fixtures. Flag "
                "contract drift, unsupported assumptions, fixture update candidates, "
                "and follow-up implementation tasks.",
                output_last_message=".agent-remote/runs/upstream-contract-refresh/report.md",
            ),
        ),
    )
    return recipe


def _skillize_workflow_recipe() -> CommandRecipe:
    """Implement skillize workflow recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="skillize-workflow",
        source=CommandSource.BUILTIN,
        description=(
            "Convert a validated command recipe or run record into a Codex local skill "
            "with SKILL.md, agents/openai.yaml, and validation evidence."
        ),
        risk=CommandRisk.WRITES_FILES,
        steps=(
            prompt_step(
                "Inspect the selected recipe/run record and draft a concise skill. Use "
                "`~/.codex/skills/<skill-name>/SKILL.md`, generate `agents/openai.yaml`, "
                "and keep only reusable procedural guidance.",
                expected_artifacts=(
                    "/Users/imhaneul/.codex/skills/<skill-name>/SKILL.md",
                    "/Users/imhaneul/.codex/skills/<skill-name>/agents/openai.yaml",
                ),
            ),
            local_step(
                (
                    "uv",
                    "run",
                    "--with",
                    "pyyaml",
                    "python",
                    "/Users/imhaneul/.codex/skills/.system/skill-creator/scripts/quick_validate.py",
                    "/Users/imhaneul/.codex/skills/<skill-name>",
                )
            ),
        ),
    )
    return recipe


def _run_ledger_closeout_recipe() -> CommandRecipe:
    """Implement run ledger closeout recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="run-ledger-closeout",
        source=CommandSource.BUILTIN,
        description=(
            "Inspect .agent-remote/runs, verify expected artifacts, prepare replay-plan "
            "evidence, and generate a final handoff closeout."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("agent-remote", "runs", "list", "--cwd", ".", "--json")),
            local_step(
                ("agent-remote", "runs", "show", "<run-id>", "--cwd", ".", "--json")
            ),
            local_step(
                (
                    "agent-remote",
                    "runs",
                    "replay-plan",
                    "<run-id>",
                    "--cwd",
                    ".",
                    "--dry-run",
                    "--json",
                )
            ),
            codex_step(
                "Build a run-ledger closeout: verify declared artifacts exist, summarize "
                "planned vs actual evidence, note replay-plan commands, and produce a "
                "handoff suitable for final report or Ultragoal checkpoint.",
                output_last_message=".agent-remote/runs/run-ledger-closeout/handoff.md",
            ),
        ),
    )
    return recipe


def _alexandria_memory_capture_recipe() -> CommandRecipe:
    """Implement alexandria memory capture recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="alexandria-memory-capture",
        source=CommandSource.BUILTIN,
        description=(
            "Capture completed PRDs, verification evidence, decisions, and route "
            "rationale into the local Alexandria Obsidian vault."
        ),
        risk=CommandRisk.WRITES_FILES,
        steps=(
            prompt_step(
                "Write a summary-only Alexandria note for the completed workflow. Store "
                "artifact paths, decisions, verification evidence, and next commands. Do "
                "not store secrets. The actual file must be written under "
                "`/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/`.",
                expected_artifacts=(
                    "/Users/imhaneul/Desktop/Alexandria/Contexts/Project Context/<descriptive-title>.md",
                ),
            ),
            prompt_step(
                "After writing the note, call alexandria_reindex_vault when available."
            ),
        ),
    )
    return recipe


def _docs_sync_guardian_recipe() -> CommandRecipe:
    """Implement docs sync guardian recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="docs-sync-guardian",
        source=CommandSource.BUILTIN,
        description=(
            "Inspect code changes and decide whether docs, examples, AGENTS.md, or "
            "Codex skills need synchronized updates."
        ),
        risk=CommandRisk.READ_ONLY,
        steps=(
            local_step(("git", "diff", "--name-only")),
            codex_step(
                "Review the changed files and determine whether docs/examples/AGENTS.md/"
                "skills need updates. Produce a required/optional/no-docs-needed verdict "
                "with exact file references and suggested patch targets.",
                output_last_message=".agent-remote/runs/docs-sync-guardian/report.md",
            ),
        ),
    )
    return recipe


def build_operations_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build operational guardrail and closeout workflow recipes.

    Returns:
        See function return annotation."""
    recipes = (
        _verify_handoff_plus_recipe(),
        _route_doctor_recipe(),
        _mcp_onboard_audit_recipe(),
        _upstream_contract_refresh_recipe(),
        _skillize_workflow_recipe(),
        _run_ledger_closeout_recipe(),
        _alexandria_memory_capture_recipe(),
        _docs_sync_guardian_recipe(),
    )
    return recipes
