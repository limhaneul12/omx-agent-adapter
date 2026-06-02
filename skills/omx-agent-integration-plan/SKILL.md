---
name: omx-agent-integration-plan
description: Use when the user mentions integration-plan or needs to merge Team/subagent outputs into decisions, conflict matrix, integration order, verification sequence, and remaining blockers.
---

# omx-agent integration-plan

Use `builtin:integration-plan` after multiple workers/subagents have produced outputs and you need an ordered merge plan.

## When to use

- Team or subagent outputs overlap or conflict.
- You need to decide merge order and verification order.
- You need an integration decision record before review.
- Company-run is moving from implementation lanes toward review-gate.

## Do not use

- Before there are multiple outputs to integrate.
- To perform arbitrary implementation.
- To skip Team evidence reading; use `team-sync` first if status is unknown.

## Standard usage

```bash
agent-remote commands show builtin:integration-plan --cwd . --json
agent-remote run builtin:integration-plan --cwd . --dry-run --task "<worker outputs and integration objective>" --json
agent-remote run builtin:integration-plan --cwd . --execute --autonomy agent --task "<worker outputs and integration objective>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:integration-plan --cwd . --execute --autonomy agent --task "<worker outputs and integration objective>" --json
```

CLI preview:

```text
comx-agent run builtin:integration-plan --task "<worker outputs and integration objective>" --cwd . --dry-run
```

## Expected artifacts

- conflict matrix
- accepted/rejected worker decisions
- integration sequence
- verification sequence
- unresolved blockers

## Output interpretation

If conflicts remain material, do not proceed to release. Resolve conflicts or assign follow-up worker tasks. If clear, proceed to `review-gate`.
