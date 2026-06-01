# Agent Remote Command Recipes

Use `comx-agent commands` to inspect the consolidated command catalog before an agent runs anything. The public workflow catalog is intentionally compressed to nine commands; maintenance lives separately under `adapter-ops <subcommand>`.

Public workflow commands:

- `route-next`
- `research-brief`
- `idea-to-prd`
- `implementation-kickoff`
- `team-sync`
- `integration-plan`
- `review-gate`
- `release-readiness`
- `company-run`

Maintenance namespace:

- `adapter-ops mcp-audit`
- `adapter-ops contract-refresh`
- `adapter-ops skillize`
- `adapter-ops run-ledger`
- `adapter-ops memory-capture`

Human flow:

```bash
comx-agent commands list --cwd .
comx-agent commands show builtin:company-run --cwd . --json
comx-agent run builtin:company-run --cwd . --dry-run --task "build an agent company" --json
comx-agent run 'builtin:adapter-ops mcp-audit' --cwd . --dry-run --task "audit MCP setup" --json
```

MCP flow for agents that should not memorize CLI syntax:

```bash
comx-agent mcp add omx_agent --cwd . -- comx-agent mcp serve --cwd "$PWD"
comx-agent mcp tools omx_agent --cwd . --execute --json
comx-agent mcp call omx_agent company_run \
  --arguments-json '{"objective":"build an agent company"}' \
  --execute --json
comx-agent mcp call omx_agent omx_agent_preview_command \
  --arguments-json '{"command_id":"builtin:review-gate","objective":"review current diff"}' \
  --execute --json
```

The adapter-owned `omx_agent` MCP server exposes canonical helpers plus generic list/show/preview tools:

- `omx_agent_list_commands`
- `omx_agent_show_command`
- `omx_agent_preview_command`
- `research_brief`
- `idea_to_prd`
- `release_readiness`
- `company_run`


Agent JSON contract example from `comx-agent commands list --cwd . --json`:

```json
{
  "commands": [
    {
      "id": "route-next",
      "qualified_id": "builtin:route-next",
      "machine_id": "route-next",
      "machine_qualified_id": "builtin:route-next",
      "source": "builtin",
      "namespace": "workflow",
      "category": "lifecycle",
      "description": "Classify a task and recommend the safest next command or runtime lane.",
      "risk": "read_only",
      "step_count": 3
    },
    {
      "id": "company-run",
      "qualified_id": "builtin:company-run",
      "machine_id": "company-run",
      "machine_qualified_id": "builtin:company-run",
      "source": "builtin",
      "namespace": "workflow",
      "category": "macro",
      "description": "Run a company-style macro orchestration loop with gates, votes, Team, subagents, review, release, and Alexandria MCP tool points.",
      "risk": "launches_runtime",
      "step_count": 2
    },
    {
      "id": "adapter-ops mcp-audit",
      "qualified_id": "builtin:adapter-ops mcp-audit",
      "machine_id": "adapter-ops:mcp-audit",
      "machine_qualified_id": "builtin:adapter-ops:mcp-audit",
      "source": "builtin",
      "namespace": "adapter-ops",
      "category": "maintenance",
      "description": "Audit MCP configuration, tool visibility, OAuth/env risks, and safe registration guidance.",
      "risk": "read_only",
      "step_count": 1
    }
  ],
  "builtin_count": 14,
  "repo_count": 0,
  "public_workflow_commands": 9,
  "lifecycle_commands": 8,
  "macro_commands": 1,
  "adapter_ops_commands": 5,
  "warnings": []
}
```

Dry-run plan example from `comx-agent run builtin:company-run --cwd . --dry-run --task "build an agent company" --json`:

```json
{
  "command_id": "company-run",
  "qualified_id": "builtin:company-run",
  "source": "builtin",
  "namespace": "workflow",
  "category": "macro",
  "description": "Run a company-style macro orchestration loop with gates, votes, Team, subagents, review, release, and Alexandria MCP tool points.",
  "risk": "launches_runtime",
  "dry_run": true,
  "steps": [
    {
      "index": 1,
      "command": "codex_exec",
      "agent": "route_strategist",
      "native_argv": ["codex", "-c", "agent_type=\"route_strategist\"", "exec", "--json", "--sandbox", "read-only"],
      "codex_search": false,
      "codex_sandbox": "read-only",
      "prompt_file": "/repo/prompt/company-run/company-run-orchestration.md",
      "prompt_exists": true,
      "prompt_sha256": "example-sha256",
      "inline_prompt": "Plan company-run macro orchestration for: build an agent company.",
      "mcp_server": null,
      "mcp_tool": null,
      "mcp_arguments": {},
      "expected_artifacts": ["/repo/.comx-agent/runs/company-run/memory-recall.md", "/repo/.comx-agent/runs/company-run/research-vote.md", "/repo/.comx-agent/runs/company-run/proceed-vote.md", "/repo/.comx-agent/runs/company-run/prd-readiness.md", "/repo/.comx-agent/runs/company-run/team-plan.md", "/repo/.comx-agent/runs/company-run/review-loop.md", "/repo/.comx-agent/runs/company-run/release-closeout.md"],
      "role_lanes": [
        {"id": "company_orchestrator", "execution": "synthesis", "purpose": "Own phase sequencing, gates, voting, decisions, and closeout.", "artifact": ".comx-agent/runs/company-run/company-run-plan.md", "approval_required": true},
        {"id": "research_council", "execution": "codex_subagent", "purpose": "Run independent research lanes and research completion vote.", "artifact": ".comx-agent/runs/company-run/research-vote.md", "approval_required": false},
        {"id": "alexandria_mcp", "execution": "alexandria_memory", "purpose": "Use Alexandria MCP tools for memory recall, librarian queries, curation, and closeout.", "artifact": ".comx-agent/runs/company-run/memory-recall.md", "approval_required": false}
      ],
      "risk": "launches_runtime",
      "blocked_reasons": []
    }
  ],
  "blocked_reasons": []
}
```
