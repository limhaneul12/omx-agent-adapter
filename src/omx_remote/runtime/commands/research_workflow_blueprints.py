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


def _codex_deep_research_recipe() -> CommandRecipe:
    """Implement codex deep research recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="codex-deep-research",
        source=CommandSource.BUILTIN,
        description=(
            "Run a Codex-only live web research pass with citations, confidence labels, "
            "and an auditable final artifact."
        ),
        risk=CommandRisk.EXTERNAL_NETWORK,
        steps=(
            codex_step(
                "Research the supplied objective using live web search. Prioritize "
                "official or upstream sources, include inline citations/source URLs, "
                "label confidence for each claim, separate evidence from inference, "
                "and finish with open questions plus recommended next workflow command.",
                output_last_message=".agent-remote/runs/codex-deep-research/final-message.md",
                search=True,
            ),
        ),
    )
    return recipe


def _omx_autoresearch_loop_recipe() -> CommandRecipe:
    """Implement omx autoresearch loop recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="omx-autoresearch-loop",
        source=CommandSource.BUILTIN,
        description=(
            "Preview a durable OMX professor/critic research loop using "
            "autoresearch-goal artifacts and pass/fail verdict gates."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            prompt_step(
                "Create an OMX autoresearch-goal mission: define topic, rubric, "
                "slug, critic pass criteria, expected sources, and completion evidence. "
                "Do not run deprecated `omx autoresearch`; use `omx autoresearch-goal`.",
                expected_artifacts=(
                    ".omx/goals/autoresearch/<slug>/mission.json",
                    ".omx/goals/autoresearch/<slug>/rubric.md",
                    ".omx/goals/autoresearch/<slug>/ledger.jsonl",
                    ".omx/goals/autoresearch/<slug>/completion.json",
                ),
            ),
            local_step(("omx", "autoresearch-goal", "--help")),
        ),
    )
    return recipe


def _research_interview_prd_recipe() -> CommandRecipe:
    """Implement research interview prd recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="research-interview-prd",
        source=CommandSource.BUILTIN,
        description=(
            "Turn an ambiguous idea into a validated PRD through research, evidence "
            "critique, deep interview, refined research, second interview, and staffing."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Stage 1: run an evidence intake and research pass. Use official, "
                "upstream, repo-local, MCP, and Alexandria evidence where available. "
                "Return cited claims, contradictions, unknowns, and source quality labels.",
                output_last_message=".agent-remote/runs/research-interview-prd/research-pass-1.md",
                search=True,
            ),
            codex_step(
                "Stage 2: act as evidence critic. Challenge source quality, recency, "
                "missing citations, contradictions, implementation risk, and user-preference "
                "decisions that research cannot resolve.",
                output_last_message=".agent-remote/runs/research-interview-prd/evidence-critic.md",
            ),
            prompt_step(
                "Stage 3: run `$deep-interview` from the evidence gaps only. Ask "
                "minimal Socratic questions that affect product scope, constraints, "
                "risk tolerance, or route selection.",
                expected_artifacts=(
                    ".agent-remote/runs/research-interview-prd/interview-1.md",
                    ".omx/context/<slug>.md",
                ),
            ),
            codex_step(
                "Stage 4: rerun/refine research using interview answers. Produce "
                "a narrowed recommendation, rejected alternatives, remaining gaps, "
                "and source-backed implementation constraints.",
                output_last_message=".agent-remote/runs/research-interview-prd/research-pass-2.md",
                search=True,
            ),
            prompt_step(
                "Stage 5: run the second decision interview only for unresolved "
                "product/architecture tradeoffs. Skip it when the refined research "
                "already makes the route unambiguous.",
                expected_artifacts=(
                    ".agent-remote/runs/research-interview-prd/interview-2.md",
                ),
            ),
            codex_step(
                "Stage 6: write a PRD, test spec, staffing plan, route recommendation, "
                "Alexandria memory summary, and explicit handoff command. Default route "
                "is Ultragoal, with OMX Team only inside stories that need durable "
                "parallel worktree/state coordination.",
                output_last_message=".agent-remote/runs/research-interview-prd/prd.md",
                expected_artifacts=(
                    ".agent-remote/runs/research-interview-prd/prd.md",
                    ".agent-remote/runs/research-interview-prd/test-spec.md",
                    ".agent-remote/runs/research-interview-prd/staffing-plan.md",
                ),
            ),
        ),
    )
    return recipe


def _company_discovery_loop_recipe() -> CommandRecipe:
    """Implement company discovery loop recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="company-discovery-loop",
        source=CommandSource.BUILTIN,
        description=(
            "Run a company-style discovery loop: research, evidence critic, deep "
            "interview, PRD/test spec, staffing plan, and Alexandria memory."
        ),
        risk=CommandRisk.LONG_RUNNING,
        steps=(
            codex_step(
                "Research the objective as a product researcher. Use official/upstream, "
                "repo-local, MCP, and Alexandria context where available. Return source "
                "quality, contradictions, and open questions.",
                output_last_message=".agent-remote/runs/company-discovery-loop/research.md",
                search=True,
            ),
            codex_step(
                "Act as evidence critic. Identify unsupported claims, stale facts, "
                "missing constraints, product assumptions, and questions that require "
                "a user decision instead of more research.",
                output_last_message=".agent-remote/runs/company-discovery-loop/evidence-critic.md",
            ),
            prompt_step(
                "Run deep interview only for the evidence gaps. Capture answers as "
                "scope, constraints, route preferences, risk tolerance, and success criteria.",
                expected_artifacts=(
                    ".agent-remote/runs/company-discovery-loop/interview.md",
                ),
            ),
            codex_step(
                "Write the final PRD, test spec, staffing plan, route recommendation, "
                "and Alexandria memory summary from the research and interview evidence.",
                output_last_message=".agent-remote/runs/company-discovery-loop/prd.md",
                expected_artifacts=(
                    ".agent-remote/runs/company-discovery-loop/prd.md",
                    ".agent-remote/runs/company-discovery-loop/test-spec.md",
                    ".agent-remote/runs/company-discovery-loop/staffing-plan.md",
                ),
            ),
        ),
    )
    return recipe


def _subagent_research_swarm_recipe() -> CommandRecipe:
    """Implement subagent research swarm recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="subagent-research-swarm",
        source=CommandSource.BUILTIN,
        description=(
            "Use Codex subagents for read-heavy research lanes, then synthesize a "
            "source-backed memo with confidence and route recommendations."
        ),
        risk=CommandRisk.EXTERNAL_NETWORK,
        steps=(
            codex_step(
                "Spawn read-only research subagents by lane: official/upstream docs, "
                "repo architecture, risks/security, alternatives/prior art. Use web search "
                "where current evidence matters. Wait for all lanes, then synthesize a "
                "cited memo with confidence and next workflow command.",
                output_last_message=".agent-remote/runs/subagent-research-swarm/synthesis.md",
                expected_artifacts=(
                    ".agent-remote/runs/subagent-research-swarm/official-docs.md",
                    ".agent-remote/runs/subagent-research-swarm/repo-architecture.md",
                    ".agent-remote/runs/subagent-research-swarm/risks.md",
                    ".agent-remote/runs/subagent-research-swarm/alternatives.md",
                ),
                search=True,
            ),
        ),
    )
    return recipe


def _dependency_incident_audit_recipe() -> CommandRecipe:
    """Implement dependency incident audit recipe behavior.

    Returns:
        See function return annotation."""
    recipe = CommandRecipe(
        id="dependency-incident-audit",
        source=CommandSource.BUILTIN,
        description=(
            "Analyze a vulnerability, advisory, or dependency incident against the repo "
            "and produce a safe patch or upgrade plan."
        ),
        risk=CommandRisk.EXTERNAL_NETWORK,
        steps=(
            codex_step(
                "Research the supplied advisory or dependency incident using official "
                "security/advisory sources when available. Map affected packages and "
                "versions to this repository, assess exploitability, propose a minimal "
                "patch/upgrade plan, and list verification commands.",
                output_last_message=".agent-remote/runs/dependency-incident-audit/report.md",
                search=True,
            ),
        ),
    )
    return recipe


def build_research_workflow_blueprints() -> tuple[CommandRecipe, ...]:
    """Build research and discovery workflow recipes.

    Returns:
        See function return annotation."""
    recipes = (
        _codex_deep_research_recipe(),
        _omx_autoresearch_loop_recipe(),
        _research_interview_prd_recipe(),
        _company_discovery_loop_recipe(),
        _subagent_research_swarm_recipe(),
        _dependency_incident_audit_recipe(),
    )
    return recipes
