# Agent Remote Command Recipes

Use `agent-remote commands` to inspect project-owned composed commands before an agent runs anything. Recipes can combine native argv, prompt files, inline prompts, Codex execution, OMX execution, and expected artifacts while keeping a typed dry-run plan available for review. When the plan is acceptable, `agent-remote run <recipe> --execute --autonomy agent` runs it through the actual execution pipeline and records attempts, stdout/stderr, artifacts, retry/recovery decisions, and handoff evidence.

Human flow:

```bash
agent-remote commands list --cwd .
agent-remote commands show review-diff --cwd .
agent-remote run review-diff --cwd . --dry-run
agent-remote run review-diff --cwd . --dry-run --json
agent-remote run route-doctor --cwd . --execute --autonomy agent --task "choose the safest route" --json
```

MCP flow for agents that should not memorize CLI syntax:

```bash
# Installed package form
comx-agent mcp add omx_agent --cwd . -- comx-agent mcp serve --cwd "$PWD"

# Development-tree form
comx-agent mcp add omx_agent --cwd . --env PYTHONPATH="$PWD/src:$PWD/src/omx_remote" --force -- \
  uv run python omx_agent_adapter_cli.py mcp serve --cwd "$PWD"

comx-agent mcp tools omx_agent --cwd . --execute --json
comx-agent mcp call omx_agent codex_deep_research \
  --arguments-json '{"objective":"research the current MCP UX for command recipes"}' \
  --execute --json
comx-agent mcp call omx_agent verify_handoff_plus \
  --arguments-json '{"notes":"final verification before handoff"}' \
  --execute --json
```

The adapter-owned `omx_agent` MCP server advertises flagship dedicated tools plus a generic preview tool:

- `omx_agent_list_commands`
- `omx_agent_show_command`
- `omx_agent_preview_command`
- `codex_deep_research`
- `omx_autoresearch_loop`
- `research_interview_prd`
- `company_build_loop`
- `verify_handoff_plus`

These MCP tools return dry-run command plans, native command previews, risk labels, blockers, and next-action hints. Use the CLI `run --execute --autonomy agent` path for actual execution; high-risk native Codex/OMX launches remain policy-gated and recorded rather than silently started from MCP preview tools.

Any built-in recipe can be previewed through the generic MCP tool:

```bash
comx-agent mcp call omx_agent omx_agent_preview_command \
  --arguments-json '{"command_id":"builtin:route-doctor","objective":"choose the safest dogfood route"}' \
  --execute --json
```

The current dogfood command family adds these future-facing built-ins:

- `route-doctor`
- `mcp-onboard-audit`
- `subagent-review-wave`
- `upstream-contract-refresh`
- `skillize-workflow`
- `run-ledger-closeout`
- `alexandria-memory-capture`
- `docs-sync-guardian`
- `dependency-incident-audit`
- `migration-checkpoint-loop`
- `company-discovery-loop`
- `company-build-loop-plus`
- `product-council`
- `team-sprint-plan`
- `subagent-research-swarm`
- `ultragoal-story-factory`
- `qa-war-room`
- `librarian-closeout`

Agent JSON contract example from `agent-remote commands list --cwd . --json`:

```json
{
  "commands": [
    {
      "id": "review-diff",
      "qualified_id": "builtin:review-diff",
      "source": "builtin",
      "description": "Review the current git diff against repository rules.",
      "risk": "read_only",
      "step_count": 1
    },
    {
      "id": "verify-handoff",
      "qualified_id": "builtin:verify-handoff",
      "source": "builtin",
      "description": "Run repo verification gates and prepare a handoff artifact.",
      "risk": "read_only",
      "step_count": 4
    },
    {
      "id": "ultragoal-roadmap",
      "qualified_id": "builtin:ultragoal-roadmap",
      "source": "builtin",
      "description": "Plan an OMX UltraGoal run from a roadmap brief file.",
      "risk": "launches_runtime",
      "step_count": 1
    },
    {
      "id": "mcp-registry-inspect",
      "qualified_id": "builtin:mcp-registry-inspect",
      "source": "builtin",
      "description": "Inspect MCP servers available to comx-agent through Codex/repo config.",
      "risk": "read_only",
      "step_count": 1
    },
    {
      "id": "codex-deep-research",
      "qualified_id": "builtin:codex-deep-research",
      "source": "builtin",
      "description": "Run a Codex-only live web research pass with citations, confidence labels, and an auditable final artifact.",
      "risk": "external_network",
      "step_count": 1
    },
    {
      "id": "omx-autoresearch-loop",
      "qualified_id": "builtin:omx-autoresearch-loop",
      "source": "builtin",
      "description": "Preview a durable OMX professor/critic research loop using autoresearch-goal artifacts and pass/fail verdict gates.",
      "risk": "long_running",
      "step_count": 2
    },
    {
      "id": "research-interview-prd",
      "qualified_id": "builtin:research-interview-prd",
      "source": "builtin",
      "description": "Turn an ambiguous idea into a validated PRD through research, evidence critique, deep interview, refined research, second interview, and staffing.",
      "risk": "long_running",
      "step_count": 6
    },
    {
      "id": "company-discovery-loop",
      "qualified_id": "builtin:company-discovery-loop",
      "source": "builtin",
      "description": "Run a company-style discovery loop: research, evidence critic, deep interview, PRD/test spec, staffing plan, and Alexandria memory.",
      "risk": "long_running",
      "step_count": 4
    },
    {
      "id": "subagent-research-swarm",
      "qualified_id": "builtin:subagent-research-swarm",
      "source": "builtin",
      "description": "Use Codex subagents for read-heavy research lanes, then synthesize a source-backed memo with confidence and route recommendations.",
      "risk": "external_network",
      "step_count": 1
    },
    {
      "id": "dependency-incident-audit",
      "qualified_id": "builtin:dependency-incident-audit",
      "source": "builtin",
      "description": "Analyze a vulnerability, advisory, or dependency incident against the repo and produce a safe patch or upgrade plan.",
      "risk": "external_network",
      "step_count": 1
    },
    {
      "id": "company-build-loop",
      "qualified_id": "builtin:company-build-loop",
      "source": "builtin",
      "description": "Preview a company-like build loop: product research, PRD/staffing, Ultragoal, optional Team, verification, code review, UltraQA, and memory.",
      "risk": "launches_runtime",
      "step_count": 4
    },
    {
      "id": "company-build-loop-plus",
      "qualified_id": "builtin:company-build-loop-plus",
      "source": "builtin",
      "description": "Run the expanded company build loop from an accepted PRD through UltraGoal, optional Team, verification, review, UltraQA, and memory closeout.",
      "risk": "launches_runtime",
      "step_count": 4
    },
    {
      "id": "subagent-review-wave",
      "qualified_id": "builtin:subagent-review-wave",
      "source": "builtin",
      "description": "Preview a Codex-native parallel review wave for security, tests, maintainability, performance, and final synthesis.",
      "risk": "long_running",
      "step_count": 1
    },
    {
      "id": "product-council",
      "qualified_id": "builtin:product-council",
      "source": "builtin",
      "description": "Run a PM/researcher/architect/critic council that decides build, no-build, or research-more before implementation.",
      "risk": "long_running",
      "step_count": 1
    },
    {
      "id": "team-sprint-plan",
      "qualified_id": "builtin:team-sprint-plan",
      "source": "builtin",
      "description": "Convert a PRD or active UltraGoal story into OMX Team lanes, owner roles, deliverables, mailbox protocol, and checkpoint expectations.",
      "risk": "launches_runtime",
      "step_count": 2
    },
    {
      "id": "ultragoal-story-factory",
      "qualified_id": "builtin:ultragoal-story-factory",
      "source": "builtin",
      "description": "Convert a PRD/test spec into UltraGoal-ready stories, acceptance criteria, verification commands, and handoff prompts.",
      "risk": "launches_runtime",
      "step_count": 2
    },
    {
      "id": "migration-checkpoint-loop",
      "qualified_id": "builtin:migration-checkpoint-loop",
      "source": "builtin",
      "description": "Split a large refactor or migration into UltraGoal checkpoints with validation gates, rollback notes, and evidence requirements.",
      "risk": "launches_runtime",
      "step_count": 2
    },
    {
      "id": "qa-war-room",
      "qualified_id": "builtin:qa-war-room",
      "source": "builtin",
      "description": "Run a multi-role verification war room after implementation and produce approve/block evidence before completion.",
      "risk": "long_running",
      "step_count": 3
    },
    {
      "id": "librarian-closeout",
      "qualified_id": "builtin:librarian-closeout",
      "source": "builtin",
      "description": "Close the loop by verifying artifacts and saving accepted decisions, PRD paths, verification evidence, and next commands to Alexandria.",
      "risk": "writes_files",
      "step_count": 3
    },
    {
      "id": "verify-handoff-plus",
      "qualified_id": "builtin:verify-handoff-plus",
      "source": "builtin",
      "description": "Run expanded verification gates, TUI/research smokes, and a final Codex review handoff summary.",
      "risk": "read_only",
      "step_count": 6
    },
    {
      "id": "route-doctor",
      "qualified_id": "builtin:route-doctor",
      "source": "builtin",
      "description": "Diagnose the safest Codex/OMX/project route for a task using catalog, route policy, preflight, runtime status, and next-action evidence.",
      "risk": "read_only",
      "step_count": 4
    },
    {
      "id": "mcp-onboard-audit",
      "qualified_id": "builtin:mcp-onboard-audit",
      "source": "builtin",
      "description": "Audit Codex and comx-agent MCP configuration, tool visibility, OAuth/env risks, redaction needs, and safe registration commands.",
      "risk": "read_only",
      "step_count": 4
    },
    {
      "id": "upstream-contract-refresh",
      "qualified_id": "builtin:upstream-contract-refresh",
      "source": "builtin",
      "description": "Run Codex/OMX probe suites and compare captured fixtures so adapter support is grounded in current observed contracts.",
      "risk": "read_only",
      "step_count": 4
    },
    {
      "id": "skillize-workflow",
      "qualified_id": "builtin:skillize-workflow",
      "source": "builtin",
      "description": "Convert a validated command recipe or run record into a Codex local skill with SKILL.md, agents/openai.yaml, and validation evidence.",
      "risk": "writes_files",
      "step_count": 2
    },
    {
      "id": "run-ledger-closeout",
      "qualified_id": "builtin:run-ledger-closeout",
      "source": "builtin",
      "description": "Inspect .agent-remote/runs, verify expected artifacts, prepare replay-plan evidence, and generate a final handoff closeout.",
      "risk": "read_only",
      "step_count": 4
    },
    {
      "id": "alexandria-memory-capture",
      "qualified_id": "builtin:alexandria-memory-capture",
      "source": "builtin",
      "description": "Capture completed PRDs, verification evidence, decisions, and route rationale into the local Alexandria Obsidian vault.",
      "risk": "writes_files",
      "step_count": 2
    },
    {
      "id": "docs-sync-guardian",
      "qualified_id": "builtin:docs-sync-guardian",
      "source": "builtin",
      "description": "Inspect code changes and decide whether docs, examples, AGENTS.md, or Codex skills need synchronized updates.",
      "risk": "read_only",
      "step_count": 2
    }
  ],
  "builtin_count": 27,
  "repo_count": 0,
  "warnings": []
}
```

Dry-run plan example from `agent-remote run review-diff --cwd . --dry-run --json
agent-remote run route-doctor --cwd . --execute --autonomy agent --task "choose the safest route" --json`:

```json
{
  "command_id": "review-diff",
  "qualified_id": "builtin:review-diff",
  "source": "builtin",
  "description": "Review the current git diff against repository rules.",
  "risk": "read_only",
  "dry_run": true,
  "steps": [
    {
      "index": 1,
      "command": "codex_exec",
      "agent": null,
      "native_argv": [
        "codex",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--output-last-message",
        ".agent-remote/runs/review-diff/final-message.md",
        "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation."
      ],
      "codex_search": false,
      "codex_sandbox": "read-only",
      "prompt_file": null,
      "prompt_exists": null,
      "prompt_sha256": null,
      "inline_prompt": "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation.",
      "mcp_server": null,
      "mcp_tool": null,
      "mcp_arguments": {},
      "expected_artifacts": [
        ".agent-remote/runs/review-diff/final-message.md"
      ],
      "risk": "read_only",
      "blocked_reasons": []
    }
  ],
  "blocked_reasons": []
}
```

Safety rule: use `--dry-run` first. Actual execution is explicit: `agent-remote run <id> --execute --autonomy agent --json`. The executor records `.agent-remote/runs/<run-id>/plan.json`, `autonomy-decision.json`, `result.json`, `artifacts.json`, `recovery.md`, and per-step attempt stdout/stderr/result files. Prompt-only and runtime-gated steps produce honest handoff artifacts and stop the run until resumed by an agent; local/Codex/MCP steps execute with bounded retry/recovery, and missing declared subprocess artifacts fail instead of being manufactured. Durable JSON/log/handoff artifacts redact secret-shaped values, Codex exec steps default to `--sandbox read-only`, and actual CLI runs return non-zero for `failed`, `blocked`, and `requires_agent_action` so shell pipelines do not continue after a failed or gated command.
