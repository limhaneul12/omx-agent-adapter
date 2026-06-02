---
name: omx-agent-route-next
description: Use when the user mentions the omx-agent route-next command, needs to classify a task, choose the safest next adapter command, or decide between Codex, OMX, Team, UltraGoal, research, PRD, review, or release lanes.
---

# omx-agent route-next

Use `builtin:route-next` as the cheap first classifier before spending tokens on research, PRD writing, Team, or company-run.

## When to use

- The user gives a task and asks “what should we run next?”
- You need to choose between `discovery-gate`, `research-brief`, `idea-to-prd`, `company-run`, or review/release commands.
- You need a read-only route recommendation with evidence, blockers, and next actions.

## Do not use

- When the next command is already explicitly chosen and safe.
- As a substitute for `discovery-gate` when the idea is ambiguous or may need deep-interview.
- As an implementation command; it is read-only planning.

## Standard usage

```bash
agent-remote commands show builtin:route-next --cwd . --json
agent-remote run builtin:route-next --cwd . --dry-run --task "<task>" --json
agent-remote run builtin:route-next --cwd . --execute --autonomy agent --task "<task>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:route-next --cwd . --execute --autonomy agent --task "<task>" --json
```

CLI preview:

```text
comx-agent run builtin:route-next --task "<task>" --cwd . --dry-run
```

## Expected behavior

- Takes a cockpit snapshot.
- Runs route recommendation.
- Uses the `route_strategist` Codex lane for a route note.
- Produces `.comx-agent/runs/route-next/route-recommendation.md` during actual execution.

## Output interpretation

Prefer the command it recommends unless new evidence shows the route is unsafe. If the task is vague or high-risk, expect `discovery-gate` or `research-brief` before PRD or implementation.
