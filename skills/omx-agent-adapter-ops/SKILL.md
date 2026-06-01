---
name: omx-agent-adapter-ops
description: Use when the user mentions adapter-ops, mcp-audit, contract-refresh, skillize, run-ledger, or memory-capture maintenance commands for omx-agent-adapter; keeps maintenance commands separate from the 10 public workflow commands.
---

# omx-agent adapter-ops

Use the `adapter-ops:*` namespace for maintenance. These commands are not counted as the 10 public workflow commands.

## Commands

- `builtin:adapter-ops:mcp-audit` — audit MCP configuration, tool visibility, OAuth/env risks, and registration guidance.
- `builtin:adapter-ops:contract-refresh` — plan probe suites and fixture comparisons for upstream Codex/OMX drift.
- `builtin:adapter-ops:skillize` — turn a validated recipe/run record into a Codex skill plan and validation handoff.
- `builtin:adapter-ops:run-ledger` — inspect run records, missing artifacts, replay evidence, and stale run notes.
- `builtin:adapter-ops:memory-capture` — capture curated project memory through Alexandria MCP tool handoff.

## When to use

- The user asks for maintenance, audit, drift detection, skill generation, run closeout, or memory capture.
- You need to keep operational hygiene separate from lifecycle/product workflows.
- You need an evidence artifact before committing, checkpointing, or closing a task.

## Do not use

- As part of the 10 public workflow command count.
- To replace `release-readiness`; release-readiness may call maintenance concerns, but remains the release gate.
- To hide missing implementation/review work.

## Standard usage

```bash
agent-remote commands show builtin:adapter-ops:mcp-audit --cwd . --json
agent-remote run builtin:adapter-ops:mcp-audit --cwd . --dry-run --task "<audit objective>" --json
agent-remote run builtin:adapter-ops:mcp-audit --cwd . --execute --autonomy agent --task "<audit objective>" --json
```

Replace `mcp-audit` with `contract-refresh`, `skillize`, `run-ledger`, or `memory-capture` as needed.

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:adapter-ops:run-ledger --cwd . --execute --autonomy agent --task "<closeout objective>" --json
```

TUI preview:

```text
/run builtin:adapter-ops:run-ledger --task "<closeout objective>"
```

## Output interpretation

Maintenance outputs should be treated as evidence or handoff artifacts. If a maintenance command finds drift, missing artifacts, or memory gaps, fix those before claiming final completion.
