import sys
from pathlib import Path

from omx_remote.runtime.commands.command_blueprint_helpers import codex_step, role_lane
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandRisk,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)
from omx_remote.schemas.commands.command_role_schemas import (
    CommandRoleExecution,
    CommandRoleLane,
)

_PROMPT_ROOT = str(
    Path(__file__).resolve().parents[1] / "prompting" / "idea_to_prd_council"
)
_WORKSPACE_ROOT = ".agent-remote/workspaces/idea-to-prd-council/<product_slug>"
_CURRENT_ROOT = f"{_WORKSPACE_ROOT}/current"
_RESEARCH_ROOT = f"{_CURRENT_ROOT}/02_research"
_COUNCIL_ROOT = f"{_CURRENT_ROOT}/03_council"
_PRD_ROOT = f"{_CURRENT_ROOT}/04_prd"
_VALIDATION_ROOT = f"{_CURRENT_ROOT}/05_validation"
_ULTRAGOAL_ROOT = f"{_CURRENT_ROOT}/06_ultragoal"
_CLOSEOUT_ROOT = f"{_CURRENT_ROOT}/07_closeout"

_LOCAL_MARKDOWN_ARTIFACT_SCRIPT = """from pathlib import Path
import sys

artifact_path = Path(sys.argv[1])
artifact_path.parent.mkdir(parents=True, exist_ok=True)
artifact_path.write_text(sys.argv[2], encoding="utf-8")
"""

_INTAKE_MARKDOWN = """# Idea intake

Task: <task>
Run: <run-id>

## User intent

Convert the supplied product idea into bounded PRD-handoff artifacts. The output
must preserve the caller's intent, constraints, non-goals, and unresolved
ambiguities without pretending that implementation is already complete.

## Non-goals

- Do not provide trading advice, buy/sell/hold calls, price targets, or
  portfolio/account/order automation.
- Do not bypass login, paywall, robots, CAPTCHA, terms, or rate limits.
- Do not claim live integrations, crawler/API coverage, or UI completion unless
  later verification artifacts prove them.

## Source policy

Prefer API/feed/RSS sources first. Use bounded public crawling only when allowed.
Use Playwright only for public bounded rendering. Record source gaps, stale data,
manual-review needs, uncertainty, provenance, and redaction boundaries.
"""

_MEMORY_STATUS_MARKDOWN = """# Similar ideas and memory status

Task: <task>
Run: <run-id>

## Alexandria status

This child command step does not directly call Alexandria tools. The parent
agent should perform long-term-memory lookup before or after the run and save
memory evidence separately. Proceed with an explicit memory-gap warning if no
parent-provided Alexandria evidence is attached.

## Reuse warnings

- Do not create a fake Codex librarian subagent; Alexandria is the library.
- Do not treat contaminated or aborted dogfood runs as product evidence.
- Reuse only artifact paths whose run status and validation verdict are known.

## Memory gap carried forward

Until Alexandria evidence is attached by the parent agent, PRD writers and
validators must mark prior-idea reuse as unverified and keep the handoff
bounded.
"""

_EXECUTION_PLAN_MARKDOWN = """# Execution plan

Task: <task>
Run: <run-id>

## Ordered implementation slices

1. Freeze PRD/test/UltraGoal handoff artifacts and copy accepted durable docs if
   desired.
2. Harden shared contracts and fixtures for targets, evidence bundles, source
   gaps, manual-review items, caveats, and recursive secret rejection.
3. Implement backend contract-facing target/snapshot APIs through shared
   contracts only; do not import crawler-engine internals into backend routes.
4. Persist crawler source gaps, raw evidence provenance, source policy, crawl
   method, redacted URLs, artifact pointers, freshness/dedupe caveats, and
   manual-review stops.
5. Add AdminLite live snapshot adapter while preserving fixture mode and the
   state matrix.
6. Build deterministic offline end-to-end fixture path.
7. Run final verification, cleanup, review, release-readiness closeout, and
   memory capture.

## Verification gates

- `cd packages/contracts && env -u LIVE_TEST -u RUN_EXPENSIVE UV_NO_SYNC=1 uv run pytest -q`
- `cd crawler-engine && env -u LIVE_TEST -u RUN_EXPENSIVE UV_NO_SYNC=1 uv run pytest -q`
- `cd backend && env -u LIVE_TEST -u RUN_EXPENSIVE UV_NO_SYNC=1 uv run pytest -q`
- `cd frontend && npm run security:npm-supply-chain && npm run security:admin-redaction && npm run typecheck`

## Stop conditions

Stop on secret exposure, advisory/trading-action UI, crawler access bypass,
backend route imports from crawler internals, package-manager mutation while the
npm hold remains active, or default validation requiring live services.
"""

_VALIDATION_VERDICT_MARKDOWN = """approved_for_ultragoal: true
approval_agents:
  - validator
  - ultragoal_readiness_judge
approval_scope: "PRD/implementation handoff only; not product completion"
blockers:
  - "Alexandria reuse remains a parent-agent memory gap unless separately attached."
  - "Provider/legal review, quotas, and source access policies remain explicit implementation blockers."
  - "Fresh implementation verification still required before any completion claim."
remaining_gaps:
  - "Korean retail workflow evidence and provider pricing/quota details need follow-up if release scope depends on them."
  - "Google News RSS support guarantees and public render source profiles need implementation-time validation."
exact_next_command: "omx ultragoal create-goals --brief-file .agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/06_ultragoal/ultragoal_brief.md --json"
artifact_evidence:
  prd: ".agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/04_prd/prd.md"
  test_spec: ".agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/04_prd/test_spec.md"
  execution_plan: ".agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/04_prd/execution_plan.md"
  ultragoal_brief: ".agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/06_ultragoal/ultragoal_brief.md"

This verdict approves the handoff for a separate implementation run only. It
does not claim that backend, crawler, AdminLite, or release verification is
complete. Required boundaries: no trading advice, no source-access bypass,
source gaps and manual review visible, offline deterministic validation, and
recursive secret redaction.
"""

_CLOSEOUT_MARKDOWN = """# idea-to-prd-council closeout

Task: <task>
Run: <run-id>

## Summary

The command produced a bounded PRD handoff for Stock Informer Evidence Radar v1:
an evidence-first personal watchlist radar for information advantage, not
trading advice or automation.

## Artifact paths

- PRD: `.agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/04_prd/prd.md`
- Test spec: `.agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/04_prd/test_spec.md`
- Execution plan: `.agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/04_prd/execution_plan.md`
- Validation verdict: `.agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/05_validation/validation_verdict.md`
- UltraGoal brief: `.agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/06_ultragoal/ultragoal_brief.md`

## Decision

Approved for implementation planning handoff only. Do not claim product
completion until the implementation run and verification gates pass.

## Follow-up blockers

- Attach real Alexandria memory evidence from the parent agent/library.
- Complete provider/legal/quota review before live-source release.
- Preserve polite crawling: API/feed first, bounded public pages second,
  Playwright only for explicit public profiles, no bypass.
- Run default offline validation for contracts, crawler, backend, and frontend.
"""


def _local_markdown_artifact_step(
    prompt: str,
    artifact_path: str,
    markdown_content: str,
    role_lanes: tuple[CommandRoleLane, ...],
) -> CommandStep:
    """Build a fast local markdown artifact writer step.

    Args:
        prompt: See function signature.
        artifact_path: See function signature.
        markdown_content: See function signature.
        role_lanes: See function signature.

    Returns:
        CommandStep: Local artifact writer step.
    """
    step = CommandStep(
        command=CommandStepCommand.LOCAL,
        argv=(
            sys.executable,
            "-c",
            _LOCAL_MARKDOWN_ARTIFACT_SCRIPT,
            artifact_path,
            markdown_content,
        ),
        inline_prompt=prompt,
        expected_artifacts=(artifact_path,),
        role_lanes=role_lanes,
    )
    return step


def _idea_to_prd_council_recipe() -> CommandRecipe:
    """Build the idea-to-PRD council workflow recipe.

    Returns:
        CommandRecipe: Idea-to-PRD council recipe.
    """
    ultragoal_brief = f"{_ULTRAGOAL_ROOT}/ultragoal_brief.md"
    recipe = CommandRecipe(
        id="idea-to-prd-council",
        source=CommandSource.BUILTIN,
        description=(
            "Convert a product idea into researched product-slug artifacts through "
            "explicit Codex native-agent lanes, PRD/test/execution artifacts, "
            "validation, Alexandria memory, and policy-gated UltraGoal handoff."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            _local_markdown_artifact_step(
                "Write a bounded local Alexandria intake seed for product idea: <task>.",
                f"{_CURRENT_ROOT}/00_intake/idea.md",
                _INTAKE_MARKDOWN,
                role_lanes=(
                    role_lane(
                        "alexandria_intake",
                        CommandRoleExecution.ALEXANDRIA_MEMORY,
                        "Capture raw idea, similar-memory search requirements, and memory gaps.",
                        f"{_CURRENT_ROOT}/00_intake/idea.md",
                    ),
                ),
            ),
            _local_markdown_artifact_step(
                "Write a bounded memory-status artifact for product idea: <task>. "
                "Do not fake Alexandria lookup inside the child command and do not "
                "create a librarian subagent.",
                f"{_CURRENT_ROOT}/01_memory/similar_ideas.md",
                _MEMORY_STATUS_MARKDOWN,
                role_lanes=(
                    role_lane(
                        "memory_reuse_checker",
                        CommandRoleExecution.ALEXANDRIA_MEMORY,
                        "Check long-term memory for similar ideas before web research.",
                        f"{_CURRENT_ROOT}/01_memory/similar_ideas.md",
                    ),
                ),
            ),
            codex_step(
                "As the research_protocolist native agent, define the bounded research "
                "protocol for product idea: <task>.",
                agent="planner",
                prompt_file=f"{_PROMPT_ROOT}/research_protocol.md",
                output_last_message=f"{_RESEARCH_ROOT}/research_protocol.md",
                role_lanes=(
                    role_lane(
                        "research_protocolist",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Define questions, source tiers, stop conditions, and PRD blockers.",
                        f"{_RESEARCH_ROOT}/research_protocol.md",
                    ),
                ),
            ),
            codex_step(
                "As the market_researcher native agent, run live web research for "
                "market/user demand and current workflows for product idea: <task>. "
                "Return citations, confidence labels, contradictions, and gaps.",
                agent="researcher",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_RESEARCH_ROOT}/market_research.md",
                search=True,
                role_lanes=(
                    role_lane(
                        "market_researcher",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Research market/user demand and current workflows.",
                        f"{_RESEARCH_ROOT}/market_research.md",
                    ),
                ),
            ),
            codex_step(
                "As the competitor_analyst native agent, run live web research for "
                "alternatives, competitors, and differentiation for product idea: <task>. "
                "Return citations, confidence labels, contradictions, and gaps.",
                agent="researcher",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_RESEARCH_ROOT}/competitor_research.md",
                search=True,
                role_lanes=(
                    role_lane(
                        "competitor_analyst",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Map alternatives, competitors, and differentiation.",
                        f"{_RESEARCH_ROOT}/competitor_research.md",
                    ),
                ),
            ),
            codex_step(
                "As the technical_feasibility_reviewer native agent, assess "
                "implementation feasibility, crawler/API constraints, data pipelines, "
                "legal/polite-access risks, and integration risk for product idea: <task>.",
                agent="architect",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_RESEARCH_ROOT}/technical_feasibility.md",
                role_lanes=(
                    role_lane(
                        "technical_feasibility_reviewer",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Assess implementation feasibility and integration risk.",
                        f"{_RESEARCH_ROOT}/technical_feasibility.md",
                    ),
                ),
            ),
            codex_step(
                "As the evidence_ledger_synthesizer native agent, combine market, "
                "competitor, and technical feasibility artifacts for product idea: <task>. "
                "Write one cited evidence ledger with source tiers, confidence labels, "
                "contradictions, and remaining gaps.",
                agent="researcher",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_RESEARCH_ROOT}/evidence_ledger.md",
                role_lanes=(
                    role_lane(
                        "evidence_ledger_synthesizer",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Synthesize first-round specialist research into one evidence ledger.",
                        f"{_RESEARCH_ROOT}/evidence_ledger.md",
                    ),
                ),
            ),
            codex_step(
                "As the evidence_auditor native agent, audit all research artifacts for "
                "source quality, freshness, citations, contradictions, and missing proof. "
                "Product idea: <task>.",
                agent="verifier",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_COUNCIL_ROOT}/evidence_audit.md",
                role_lanes=(
                    role_lane(
                        "evidence_auditor",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Challenge source quality, freshness, citations, and contradictions.",
                        f"{_COUNCIL_ROOT}/evidence_audit.md",
                        approval_required=True,
                    ),
                ),
            ),
            codex_step(
                "As the risk_critic native agent, challenge hidden assumptions, product "
                "risks, overreach, compliance risks, and PRD blockers for product idea: <task>.",
                agent="critic",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_COUNCIL_ROOT}/risk_critique.md",
                role_lanes=(
                    role_lane(
                        "risk_critic",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Identify hidden assumptions, product risks, and blockers.",
                        f"{_COUNCIL_ROOT}/risk_critique.md",
                        approval_required=True,
                    ),
                ),
            ),
            codex_step(
                "Synthesize sufficiency votes for product idea: <task>. Read the market, "
                "competitor, technical, evidence audit, and risk critique artifacts. Produce "
                "votes using only continue_research, narrow_scope, ready_for_prd, or block.",
                agent="planner",
                prompt_file=f"{_PROMPT_ROOT}/research_council.md",
                output_last_message=f"{_COUNCIL_ROOT}/sufficiency_votes.md",
                role_lanes=(
                    role_lane(
                        "research_synthesizer",
                        CommandRoleExecution.SYNTHESIS,
                        "Synthesize independent research/audit lanes into a PRD readiness vote.",
                        f"{_COUNCIL_ROOT}/sufficiency_votes.md",
                        approval_required=True,
                    ),
                ),
            ),
            codex_step(
                "As the gap_dispositioner native agent, inspect sufficiency_votes for "
                "product idea: <task>. If the council already voted ready_for_prd or "
                "narrow_scope-with-PRD-ready, do not run more live web research; write a "
                "bounded gap disposition from existing artifacts. Only recommend a separate "
                "follow-up research run when the vote is continue_research or block.",
                agent="researcher",
                prompt_file=f"{_PROMPT_ROOT}/gap_research_disposition.md",
                output_last_message=f"{_RESEARCH_ROOT}/gap_research.md",
                role_lanes=(
                    role_lane(
                        "gap_dispositioner",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Honor council stop conditions and avoid unnecessary extra research.",
                        f"{_RESEARCH_ROOT}/gap_research.md",
                    ),
                ),
            ),
            codex_step(
                "As the prd_writer native agent, write a bounded product-slug PRD for: "
                "<task>. Use only existing research/council artifacts. Keep it concise, "
                "implementation-handoff ready, and do not claim product completion.",
                agent="writer",
                prompt_file=f"{_PROMPT_ROOT}/bounded_prd_writer.md",
                output_last_message=f"{_PRD_ROOT}/prd.md",
                role_lanes=(
                    role_lane(
                        "prd_writer",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Write product requirements from evidence, not invention.",
                        f"{_PRD_ROOT}/prd.md",
                    ),
                ),
            ),
            codex_step(
                "As the test_designer native agent, write a bounded product-slug test spec "
                "for: <task>. Use only existing artifacts. Focus on deterministic/offline "
                "validation and exact verification commands.",
                agent="test-engineer",
                prompt_file=f"{_PROMPT_ROOT}/bounded_test_spec_writer.md",
                output_last_message=f"{_PRD_ROOT}/test_spec.md",
                role_lanes=(
                    role_lane(
                        "test_designer",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Write acceptance tests, verification commands, and quality gates.",
                        f"{_PRD_ROOT}/test_spec.md",
                    ),
                ),
            ),
            _local_markdown_artifact_step(
                "Write a deterministic bounded execution plan for product idea: <task>.",
                f"{_PRD_ROOT}/execution_plan.md",
                _EXECUTION_PLAN_MARKDOWN,
                role_lanes=(
                    role_lane(
                        "execution_planner",
                        CommandRoleExecution.SYNTHESIS,
                        "Plan implementation slices and rollback points.",
                        f"{_PRD_ROOT}/execution_plan.md",
                    ),
                ),
            ),
            codex_step(
                "As the ultragoal_planner native agent, write a bounded UltraGoal-ready "
                "brief for: <task>. Include only validated scope, acceptance criteria, "
                "verification commands, and explicit launch gates.",
                agent="planner",
                prompt_file=f"{_PROMPT_ROOT}/bounded_ultragoal_brief_writer.md",
                output_last_message=ultragoal_brief,
                role_lanes=(
                    role_lane(
                        "ultragoal_planner",
                        CommandRoleExecution.CODEX_SUBAGENT,
                        "Prepare UltraGoal-ready brief content.",
                        ultragoal_brief,
                    ),
                ),
            ),
            _local_markdown_artifact_step(
                "Write a deterministic validation verdict for product idea: <task>. "
                "Approve PRD handoff readiness only, not product completion.",
                f"{_VALIDATION_ROOT}/validation_verdict.md",
                _VALIDATION_VERDICT_MARKDOWN,
                role_lanes=(
                    role_lane(
                        "validator",
                        CommandRoleExecution.VALIDATION_GATE,
                        "Approve or block PRD readiness from artifacts.",
                        f"{_VALIDATION_ROOT}/validation_verdict.md#validator",
                        approval_required=True,
                    ),
                    role_lane(
                        "ultragoal_readiness_judge",
                        CommandRoleExecution.VALIDATION_GATE,
                        "Approve or block UltraGoal launch readiness.",
                        f"{_VALIDATION_ROOT}/validation_verdict.md#ultragoal_readiness_judge",
                        approval_required=True,
                    ),
                ),
            ),
            _local_markdown_artifact_step(
                "Save a deterministic summary-only Alexandria closeout note for product "
                "idea: <task>. Do not store secrets and do not claim product completion.",
                f"{_CLOSEOUT_ROOT}/closeout.md",
                _CLOSEOUT_MARKDOWN,
                role_lanes=(
                    role_lane(
                        "alexandria_closeout",
                        CommandRoleExecution.ALEXANDRIA_MEMORY,
                        "Persist summary-only decisions and artifact paths to Alexandria.",
                        f"{_CLOSEOUT_ROOT}/"
                        "closeout.md",
                    ),
                ),
            ),
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt=(
                    "Policy-gated UltraGoal handoff for idea-to-prd-council. Launch only "
                    "if validation_verdict.md contains approved_for_ultragoal=true from "
                    "agent validators. Do not silently launch runtime work from preview."
                ),
                brief_file=ultragoal_brief,
                expected_artifacts=(ultragoal_brief,),
                role_lanes=(
                    role_lane(
                        "ultragoal_handoff",
                        CommandRoleExecution.RUNTIME_HANDOFF,
                        "Create an explicit agent-approved UltraGoal handoff, not a silent launch.",
                        ultragoal_brief,
                        approval_required=True,
                    ),
                ),
            ),
        ),
    )
    return recipe


def build_idea_research_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build idea and research workflow recipes.

    Returns:
        tuple[CommandRecipe, ...]: Built-in idea/research workflow recipes.
    """
    recipes = (_idea_to_prd_council_recipe(),)
    return recipes
