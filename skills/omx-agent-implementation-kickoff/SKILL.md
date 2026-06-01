---
name: omx-agent-implementation-kickoff
description: Use when the user mentions implementation-kickoff or needs to convert accepted PRD, test spec, and execution brief into a policy-gated development handoff with Team/UltraGoal readiness and clean-worktree checks.
---

# omx-agent implementation-kickoff

Use `builtin:implementation-kickoff` only after planning artifacts are accepted. This is the development-start gate.

## When to use

- PRD, test spec, and execution brief exist.
- You need to assign implementation lanes.
- You need Team/UltraGoal handoff evidence.
- You need to check whether development can safely start.

## Do not use

- Before PRD/test spec/execution brief exist.
- To bypass review of planning artifacts.
- From a dirty worktree when live Team fanout is expected.

## Standard usage

```bash
agent-remote commands show builtin:implementation-kickoff --cwd . --json
agent-remote run builtin:implementation-kickoff --cwd . --dry-run --task "<accepted PRD or implementation objective>" --json
agent-remote run builtin:implementation-kickoff --cwd . --execute --autonomy agent --task "<accepted PRD or implementation objective>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:implementation-kickoff --cwd . --execute --autonomy agent --task "<accepted PRD or implementation objective>" --json
```

TUI preview:

```text
/run builtin:implementation-kickoff --task "<accepted PRD or implementation objective>"
```

## Expected behavior

- Produces a policy-gated development handoff.
- Emits runtime/Team guidance instead of silently launching unsafe work.
- Requires clean worktree discipline for Team split.

## Output interpretation

If status is `requires_agent_action`, treat it as a handoff, not success. Continue only after the required runtime/Team action is complete and recorded.
