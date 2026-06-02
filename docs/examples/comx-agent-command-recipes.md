# Agent Remote Command Recipes

Use `comx-agent commands` to inspect the consolidated command catalog before an agent runs anything. The public workflow catalog is intentionally compressed to ten commands; maintenance lives separately under `adapter-ops <subcommand>`.

Public workflow commands:

- `route-next`
- `discovery-gate`
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
comx-agent run builtin:discovery-gate --cwd . --dry-run --task "clarify an agent company idea" --json
comx-agent run builtin:company-run --cwd . --dry-run --task "build an agent company" --json
comx-agent run builtin:company-run --cwd . --execute --autonomy agent --task "build an agent company" --model gpt-5.5 --xhigh --json
comx-agent run 'builtin:adapter-ops mcp-audit' --cwd . --dry-run --task "audit MCP setup" --json
```

Runtime model controls are explicit CLI request options, not hidden project defaults:

```bash
comx-agent run builtin:research-brief --cwd . --dry-run --task "compare evidence" --model gpt-5.5 --reasoning-effort high --json
comx-agent run builtin:company-run --cwd . --execute --autonomy agent --task "ship the plan" --model gpt-5.5 --xhigh --json
```

`--madmax` is intentionally explicit and dangerous. It requests xhigh reasoning and passes Codex approval/sandbox bypass to Codex-backed steps. For `company-run`, the adapter also records the runtime option contract and forwards worker launch args to native OMX Team workers through a transient subprocess environment override.

MCP client flow for agents that need external tool access:

```bash
comx-agent mcp add local_docs --cwd . -- uvx example-mcp-server
comx-agent mcp tools local_docs --cwd . --execute --json
comx-agent mcp call local_docs search \
  --arguments-json '{"query":"release checklist"}' \
  --execute --json
```

The adapter does not expose its own MCP server. Use `comx-agent commands show` and `comx-agent run --dry-run` for adapter workflow previews; use `comx-agent mcp` only to consume external MCP servers such as Alexandria, Codex-registered servers, or repo-local tools.


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
      "description": "Run a build-oriented company-style macro loop with discovery/ROI gates, internal governance, Team, subagents, review, release, and Alexandria MCP tool points.",
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
  "builtin_count": 15,
  "repo_count": 0,
  "public_workflow_commands": 10,
  "lifecycle_commands": 9,
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
  "description": "Run a build-oriented company-style macro loop with discovery/ROI gates, internal governance, Team, subagents, review, release, and Alexandria MCP tool points.",
  "risk": "launches_runtime",
  "dry_run": true,
  "runtime_options": null,
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
      "expected_artifacts": ["/repo/.comx-agent/runs/company-run/memory-recall.md", "/repo/.comx-agent/runs/company-run/discovery/discovery-decision-packet.json", "/repo/.comx-agent/runs/company-run/discovery/roi-no-build-gate.json", "/repo/.comx-agent/runs/company-run/decisions/discovery-decision-report.md", "/repo/.comx-agent/runs/company-run/research-vote.md", "/repo/.comx-agent/runs/company-run/proceed-vote.md", "/repo/.comx-agent/runs/company-run/prd-readiness.md", "/repo/.comx-agent/runs/company-run/team-plan.md", "/repo/.comx-agent/runs/company-run/review-loop.md", "/repo/.comx-agent/runs/company-run/release-closeout.md"],
      "role_lanes": [
        {"id": "company_orchestrator", "execution": "synthesis", "purpose": "Own phase sequencing, discovery/ROI gates, internal decisions, and closeout.", "artifact": ".comx-agent/runs/company-run/company-run-plan.md", "approval_required": true},
        {"id": "research_council", "execution": "codex_subagent", "purpose": "Run independent research lanes and internal research decision record.", "artifact": ".comx-agent/runs/company-run/research-vote.md", "approval_required": false},
        {"id": "alexandria_mcp", "execution": "alexandria_memory", "purpose": "Use Alexandria MCP tools for memory recall, librarian queries, curation, and closeout.", "artifact": ".comx-agent/runs/company-run/memory-recall.md", "approval_required": false}
      ],
      "risk": "launches_runtime",
      "blocked_reasons": []
    }
  ],
  "blocked_reasons": []
}
```
