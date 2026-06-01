---
name: omx-agent-team-sync
description: Use when the user mentions team-sync or needs a read-only summary of OMX Team workers, blockers, mailbox/task state, progress, evidence, and next orchestration action.
---

# omx-agent team-sync

Use `builtin:team-sync` to read Team state and summarize worker progress without mutating work.

## When to use

- OMX Team is active or recently ran.
- You need worker status, blockers, proof layers, or mailbox evidence.
- Company-run is in implementation loop and needs periodic coordination.
- You need to decide whether to assign more work, integrate, review, or stop.

## Do not use

- To start Team; use `implementation-kickoff` or `company-run` for launch/handoff.
- To edit worker outputs.
- As a replacement for `integration-plan` when outputs need conflict resolution.

## Standard usage

```bash
agent-remote commands show builtin:team-sync --cwd . --json
agent-remote run builtin:team-sync --cwd . --dry-run --task "<team name or sync objective>" --json
agent-remote run builtin:team-sync --cwd . --execute --autonomy agent --task "<team name or sync objective>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:team-sync --cwd . --execute --autonomy agent --task "<team name or sync objective>" --json
```

TUI preview:

```text
/run builtin:team-sync --task "<team name or sync objective>"
```

## Expected behavior

- Reads active/recent Team evidence.
- Summarizes worker state, blockers, claims, and proof layers.
- Produces a sync note under `.comx-agent/runs/team-sync/` during actual execution.

## Output interpretation

Use the result to choose one next action: assign next task, wait, resolve blocker, run `integration-plan`, run `review-gate`, or close the Team loop.
