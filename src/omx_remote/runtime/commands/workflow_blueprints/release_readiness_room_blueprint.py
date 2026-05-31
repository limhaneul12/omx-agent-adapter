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


def build_release_readiness_room_recipe() -> CommandRecipe:
    """Build the release readiness room workflow recipe.

    Returns:
        CommandRecipe: Release readiness room recipe.
    """
    recipe = CommandRecipe(
        id="release-readiness-room",
        source=CommandSource.BUILTIN,
        description=(
            "Compose verification, review, docs sync, run-ledger evidence, "
            "Alexandria closeout, and final release approve/block verdict."
        ),
        risk=CommandRisk.WRITES_FILES,
        steps=(
            local_step(("git", "diff", "--check")),
            local_step(("uv", "run", "ruff", "check", "src", "tests")),
            local_step(("uv", "run", "pyrefly", "check", "src")),
            local_step(("uv", "run", "pytest", "tests/commands", "tests/comx", "-q")),
            local_step(("agent-remote", "runs", "list", "--cwd", ".", "--json")),
            codex_step(
                "Release readiness room for: <task>. Run a role-separated release "
                "council over verification_results, review_board_verdict, "
                "docs_verdict, run_ledger_evidence, Alexandria closeout needs, "
                "blockers, remaining_risks, approve_block_verdict, and next_command. "
                "Do not mark approved unless all required evidence is present.",
                output_last_message=(
                    ".agent-remote/runs/release-readiness-room/"
                    "<slug>_release_verdict.md"
                ),
            ),
            prompt_step(
                "Alexandria closeout handoff. Save summary-only decisions, artifact "
                "paths, verification evidence, release verdict, and next commands to "
                "Alexandria. Alexandria is the memory/library system; do not create "
                "a Codex librarian subagent and do not store secrets.",
                expected_artifacts=(
                    ".agent-remote/runs/release-readiness-room/"
                    "<slug>_verification_evidence.md",
                    ".agent-remote/runs/release-readiness-room/"
                    "<slug>_review_board_verdict.md",
                    ".agent-remote/runs/release-readiness-room/<slug>_docs_verdict.md",
                    ".agent-remote/runs/release-readiness-room/"
                    "<slug>_run_ledger_evidence.md",
                    ".agent-remote/runs/release-readiness-room/"
                    "<slug>_alexandria_closeout.md",
                ),
            ),
        ),
    )
    return recipe
